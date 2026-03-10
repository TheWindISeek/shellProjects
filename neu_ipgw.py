#!/usr/bin/env python3
import urllib.request
import urllib.parse
import urllib.error
import json
import re
import ssl
import http.cookiejar
import http.client
import os
import base64
import sys
import time
import hashlib
import hmac

# 默认账号密码（可直接用 1 登录，无需每次输入；可通过菜单 4 更换帐号）
DEFAULT_USERNAME = "2472067"
DEFAULT_PASSWORD = "1Smart031337"
# 网关 AC 编号，与浏览器成功页 srun_portal_success?ac_id= 一致（东北大学当前为 16）
DEFAULT_AC_ID = "16"
NEU_SSO_PUBLIC_KEY_B64 = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnjA28DLKXZzxbKmo9/1W"
    "kVLf1mr+wtLXLXt6sC4WiBCtsbzF5ewm7ARZeAdS3iZtqlYPn6IcUoOw42H8nAK"
    "/tfFcIb6dZ1K0atn0U39oWCGPzYuKtLJeMuNZiDXVuAXtojrckOjLW9B3gUnaNGL"
    "uIx0fYe66l0o9WjU2cGLNZQfiIxs2h00z1EA9IdSnVxiVQWSD+lsP3JZXh2TT287"
    "la4Y4603SQNKTK/QvXfcmccwTEd1IW6HwGxD6QrkInBiHisKWxmveN7UDSaQRZ/J"
    "97G0YC32pD38WT53izXeK0p/kU/X37VP555um1wVWFvPIuc9I7gMP1+hq5a+X6c+"
    "+tQIDAQAB"
)


def _rsa_encrypt(plaintext):
    """使用统一认证公钥 RSA 加密，返回 Base64 字符串（与前端 JSEncrypt 行为一致）"""
    try:
        from cryptography.hazmat.primitives.serialization import load_der_public_key
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError:
        raise Exception(
            "登录需要 RSA 加密，请先安装: pip install cryptography"
        )
    key_der = base64.b64decode(NEU_SSO_PUBLIC_KEY_B64)
    pub = load_der_public_key(key_der)
    ciphertext = pub.encrypt(plaintext.encode("utf-8"), padding.PKCS1v15())
    return base64.b64encode(ciphertext).decode("ascii")


def _parse_gateway_html_hint(html):
    """从网关返回的 HTML 里提取 CONFIG 中的 ip，仅用于简短提示"""
    ip_match = re.search(r'ip\s*:\s*"([^"]+)"', html)
    return "网关识别 IP: {}".format(ip_match.group(1) if ip_match else "?")


class _RawSetCookieHandler(urllib.request.BaseHandler):
    """http.cookiejar 会静默丢弃包含 | 等特殊字符的 cookie 值（如 Go gorilla securecookie）。
    此 handler 在 HTTPCookieProcessor 之后运行，手动补回被丢弃的 cookie。"""
    handler_order = 999

    def __init__(self, cookie_jar):
        self.cookie_jar = cookie_jar

    def http_response(self, request, response):
        self._rescue_cookies(request, response)
        return response

    https_response = http_response

    def _rescue_cookies(self, request, response):
        host = urllib.parse.urlparse(request.full_url).hostname or ""
        raw_cookies = response.headers.get_all("Set-Cookie") if hasattr(response.headers, "get_all") else []
        if not raw_cookies:
            return
        for line in raw_cookies:
            parts = line.split(";")
            nv = parts[0].strip()
            if "=" not in nv:
                continue
            name, value = nv.split("=", 1)
            name, value = name.strip(), value.strip()
            already = any(
                ck.name == name and host in (ck.domain or "")
                for ck in self.cookie_jar
            )
            if already:
                continue
            path = "/"
            secure = False
            for attr in parts[1:]:
                a = attr.strip().lower()
                if a.startswith("path="):
                    path = attr.strip().split("=", 1)[1].strip()
                elif a == "secure":
                    secure = True
            c = http.cookiejar.Cookie(
                version=0, name=name, value=value,
                port=None, port_specified=False,
                domain=host, domain_specified=True, domain_initial_dot=False,
                path="/", path_specified=True,
                secure=secure, expires=None, discard=True,
                comment=None, comment_url=None, rest={},
            )
            self.cookie_jar.set_cookie(c)


# ── srun 门户协议加密函数 ──────────────────────────────────────────────────

_SRUN_ALPHA = 'LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA'
_STD_ALPHA = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'


def _srun_s(a, b):
    c = len(a)
    v = []
    for i in range(0, c, 4):
        val = ord(a[i])
        if i + 1 < c:
            val |= ord(a[i + 1]) << 8
        if i + 2 < c:
            val |= ord(a[i + 2]) << 16
        if i + 3 < c:
            val |= ord(a[i + 3]) << 24
        v.append(val)
    if b:
        v.append(c)
    return v


def _srun_l(a, b):
    d = len(a)
    c = (d - 1) << 2
    if b:
        m = a[d - 1]
        if m < c - 3 or m > c:
            return None
        c = m
    chars = []
    for i in range(d):
        chars.append(chr(a[i] & 0xff))
        chars.append(chr((a[i] >> 8) & 0xff))
        chars.append(chr((a[i] >> 16) & 0xff))
        chars.append(chr((a[i] >> 24) & 0xff))
    if b:
        return ''.join(chars[:c])
    return ''.join(chars)


def _srun_xencode(msg, key):
    """XXTEA encryption used by srun portal"""
    if not msg:
        return ''
    v = _srun_s(msg, True)
    k = _srun_s(key, False)
    while len(k) < 4:
        k.append(0)
    n = len(v) - 1
    z = v[n]
    delta = 0x9E3779B9
    q = 6 + 52 // (n + 1)
    d = 0
    while q > 0:
        d = (d + delta) & 0xFFFFFFFF
        e = (d >> 2) & 3
        for p in range(n):
            y = v[p + 1]
            m = ((z >> 5) ^ (y << 2)) + (((y >> 3) ^ (z << 4)) ^ (d ^ y)) + (k[(p & 3) ^ e] ^ z)
            v[p] = (v[p] + m) & 0xFFFFFFFF
            z = v[p]
        y = v[0]
        m = ((z >> 5) ^ (y << 2)) + (((y >> 3) ^ (z << 4)) ^ (d ^ y)) + (k[(n & 3) ^ e] ^ z)
        v[n] = (v[n] + m) & 0xFFFFFFFF
        z = v[n]
        q -= 1
    return _srun_l(v, False)


def _srun_base64(raw_str):
    """Base64 encode with srun custom alphabet"""
    data = bytes(ord(c) & 0xff for c in raw_str)
    encoded = base64.b64encode(data).decode('ascii')
    trans = str.maketrans(_STD_ALPHA, _SRUN_ALPHA)
    return encoded.translate(trans)


def _parse_jsonp(text):
    text = text.strip()
    m = re.search(r'\((\{.*\})\)\s*;?\s*$', text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    try:
        return json.loads(text)
    except ValueError:
        return {}


class NEUGateway:
    """Python 3.6.5 兼容版本的网关类"""
    
    def __init__(self):
        # 创建支持cookie的opener
        self.cookie_jar = http.cookiejar.CookieJar()
        
        # 创建一个忽略SSL证书验证的上下文
        context = ssl._create_unverified_context()
        
        # 创建支持HTTPS的处理器
        https_handler = urllib.request.HTTPSHandler(context=context)
        
        # 创建opener，包含cookie处理器、HTTPS处理器、以及手动cookie补救处理器
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            https_handler,
            _RawSetCookieHandler(self.cookie_jar),
        )
        
        # 基础URL（与浏览器一致使用 https）
        self.sso_url = "https://pass.neu.edu.cn/tpass/login"
        self.portal_url = "https://ipgw.neu.edu.cn"
        
        # 设置基础请求头（尽量模拟浏览器）
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }

    def _ipgw_raw_request(self, method, path, cookies=None, extra_headers=None,
                          body_data=None, follow_redirects=5, debug_label=""):
        """用 http.client 直接请求 ipgw.neu.edu.cn，返回 (status, body, cookies_dict, all_raw_headers_list)。
        all_raw_headers_list 是最终响应的 [(name, value), ...] 原始列表。"""
        ctx = ssl._create_unverified_context()
        merged = dict(cookies) if cookies else {}
        raw_hdrs_out = []
        for _redir in range(follow_redirects + 1):
            conn = http.client.HTTPSConnection("ipgw.neu.edu.cn", context=ctx)
            hdrs = self.headers.copy()
            if extra_headers:
                hdrs.update(extra_headers)
            if merged:
                hdrs["Cookie"] = "; ".join("{}={}".format(k, v) for k, v in merged.items())
            conn.request(method, path, body=body_data, headers=hdrs)
            resp = conn.getresponse()
            body = resp.read().decode("utf-8", errors="ignore")
            raw_hdrs_out = resp.getheaders()
            for key, value in raw_hdrs_out:
                if key.lower() == "set-cookie":
                    nv = value.split(";")[0].strip()
                    if "=" in nv:
                        n, v = nv.split("=", 1)
                        merged[n.strip()] = v.strip()
            conn.close()
            if resp.status in (301, 302, 303, 307, 308):
                location = resp.getheader("Location") or ""
                if location.startswith("http"):
                    parsed_loc = urllib.parse.urlparse(location)
                    path = parsed_loc.path
                    if parsed_loc.query:
                        path += "?" + parsed_loc.query
                elif location.startswith("/"):
                    path = location
                else:
                    break
                method = "GET"
                body_data = None
                continue
            break
        return resp.status, body, merged, raw_hdrs_out

    def _ipgw_raw_get(self, path, cookies=None, extra_headers=None, follow_redirects=5):
        """便捷封装：GET 请求，返回 (status, body, cookies_dict)"""
        status, body, cookies_out, _ = self._ipgw_raw_request(
            "GET", path, cookies=cookies, extra_headers=extra_headers,
            follow_redirects=follow_redirects)
        return status, body, cookies_out

    def _init_portal_session(self):
        """预访问 IPGW 门户页，建立 mysession 会话 cookie"""
        try:
            init_url = "{}/srun_portal_pc?ac_id={}".format(self.portal_url, DEFAULT_AC_ID)
            self._make_request(init_url)
        except Exception:
            pass

    def _normalize_ipgw_cookies(self):
        """将所有 ipgw.neu.edu.cn 域的 cookie 路径统一为 /，
        防止 Path=/srun_portal_sso 的 cookie 在请求 /v1/... 时不被携带"""
        fixed = []
        for ck in self.cookie_jar:
            if "ipgw.neu.edu.cn" in (ck.domain or ""):
                if ck.path != "/":
                    fixed.append(http.cookiejar.Cookie(
                        version=0, name=ck.name, value=ck.value,
                        port=None, port_specified=False,
                        domain=ck.domain,
                        domain_specified=ck.domain_specified,
                        domain_initial_dot=ck.domain_initial_dot,
                        path="/", path_specified=True,
                        secure=ck.secure, expires=ck.expires,
                        discard=ck.discard,
                        comment=None, comment_url=None, rest={},
                    ))
        for c in fixed:
            self.cookie_jar.set_cookie(c)

    def _dump_cookies(self, label=""):
        """将 cookie jar 中的 cookie 信息以文本返回，用于调试"""
        lines = []
        for ck in self.cookie_jar:
            lines.append("  {} = {}...  domain={} path={} secure={}".format(
                ck.name, (ck.value or "")[:40], ck.domain, ck.path, ck.secure
            ))
        return "{} cookie jar ({}):\n{}".format(
            label, len(lines), "\n".join(lines) if lines else "  (空)"
        )

    def _save_debug(self, filename, content):
        """将调试信息保存到本地文件，方便你用浏览器打开对比"""
        try:
            # 统一放在当前目录的 debug 子目录下
            debug_dir = os.path.join(os.path.dirname(__file__), "debug")
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            path = os.path.join(debug_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            # 调试辅助，不影响主流程
            pass

    def _make_request(self, url, data=None, headers=None):
        """发送HTTP请求并返回响应内容"""
        body, _ = self._make_request_with_headers(url, data=data, headers=headers)
        return body

    def _make_request_with_headers(self, url, data=None, headers=None):
        """发送请求并返回 (响应体, 响应头 dict)"""
        if headers is None:
            request_headers = self.headers.copy()
        else:
            request_headers = self.headers.copy()
            request_headers.update(headers)

        if data:
            data = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=request_headers)
        else:
            req = urllib.request.Request(url, headers=request_headers)

        try:
            with self.opener.open(req) as response:
                body = response.read().decode('utf-8', errors="ignore")
                # 收集所有 Set-Cookie 和普通头（仅保留小写 key 的单一 dict）
                resp_headers = {}
                for k, v in response.headers.items():
                    resp_headers[k.lower()] = v
                # 保留 set-cookie 为列表（可能多条）
                raw = response.headers
                set_cookies = raw.get_all('Set-Cookie') if hasattr(raw, 'get_all') else ([raw.get('Set-Cookie')] if raw.get('Set-Cookie') else [])
                if set_cookies:
                    resp_headers['set-cookie'] = set_cookies
                return body, resp_headers
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            # 把异常响应也保存下来方便你排查
            self._save_debug("http_error_{}.html".format(e.code), body)
            raise Exception("HTTP {} 错误，详情见 debug/http_error_{}.html".format(e.code, e.code))
        except urllib.error.URLError as e:
            raise Exception("请求失败: {}".format(str(e)))

    def _make_request_no_redirect(self, url, data=None, headers=None):
        """发送 POST 请求且不跟随 302，用于登录后从 Location 取 ticket"""
        if headers is None:
            request_headers = self.headers.copy()
        else:
            request_headers = self.headers.copy()
            request_headers.update(headers)
        if data:
            data = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=request_headers)
        else:
            req = urllib.request.Request(url, headers=request_headers)

        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None  # 不跟随，让 open 得到 302 响应

        no_redirect_opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
            NoRedirectHandler,
        )
        try:
            resp = no_redirect_opener.open(req)
            return resp.read().decode("utf-8", errors="ignore"), resp.geturl()
        except urllib.error.HTTPError as e:
            if e.code == 302:
                location = e.headers.get("Location") or e.headers.get("location")
                if location:
                    return None, location
            body = e.read().decode("utf-8", errors="ignore")
            self._save_debug("http_error_{}.html".format(e.code), body)
            raise Exception("HTTP {}，详情见 debug/http_error_{}.html".format(e.code, e.code))
        except urllib.error.URLError as e:
            raise Exception("请求失败: {}".format(str(e)))

    def _get_login_page_params(self, service_url=None):
        """获取登录页的 lt、execution，并保存页面到 debug 目录"""
        if service_url is None:
            service_url = "http://ipgw.neu.edu.cn/srun_portal_sso"
        service_param = urllib.parse.quote(service_url, safe='')
        sso_url_with_service = "{}?service={}".format(self.sso_url, service_param)

        response = self._make_request(sso_url_with_service)
        self._save_debug("sso_login_page.html", response)

        lt_match = re.search(r'name="lt" value="(.*?)"', response)
        if not lt_match:
            snippet = response[:500].replace("\n", " ")
            raise Exception("无法获取 lt，页面结构可能变更。前500字符：{}".format(snippet))
        lt = lt_match.group(1)

        execution_match = re.search(r'name="execution" value="(.*?)"', response)
        execution = execution_match.group(1) if execution_match else "e1s1"

        return {"lt": lt, "execution": execution}

    def _cas_validate_ticket(self, ticket, service_url):
        """手动调用 CAS serviceValidate 验证 ticket，返回 (success, xml_response)"""
        validate_url = "https://pass.neu.edu.cn/tpass/serviceValidate?ticket={}&service={}".format(
            urllib.parse.quote(ticket, safe=''),
            urllib.parse.quote(service_url, safe=''),
        )
        ctx = ssl._create_unverified_context()
        conn = http.client.HTTPSConnection("pass.neu.edu.cn", context=ctx)
        conn.request("GET", validate_url.split("pass.neu.edu.cn", 1)[1],
                      headers={"User-Agent": self.headers["User-Agent"]})
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="ignore")
        conn.close()
        return resp.status, body

    def login(self, username, password):
        """CAS SSO 登录：先从 IPGW 获取正确的 CAS service URL，再用它获取 ticket"""
        try:
            # 步骤 1: 向 IPGW 查询 CAS 登录地址（获取服务器端配置的 service URL）
            st0, body0, _, _ = self._ipgw_raw_request(
                "GET", "/v1/srun_portal_sso?ac_id=" + DEFAULT_AC_ID,
                extra_headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                })
            info0 = json.loads(body0)
            redirect_url = info0.get("Redirect", "")
            if not redirect_url:
                return {"success": False, "message": "IPGW 未返回 CAS Redirect: {}".format(body0[:200])}

            svc_m = re.search(r"[?&]service=([^&]+)", redirect_url)
            if not svc_m:
                return {"success": False, "message": "无法解析 service URL: {}".format(redirect_url[:200])}
            service_url = urllib.parse.unquote(svc_m.group(1))

            # 步骤 2: 用 IPGW 给出的 service URL 进行 CAS 登录
            params = self._get_login_page_params()
            login_data = {
                "rsa": _rsa_encrypt(username + password),
                "ul": len(username),
                "pl": len(password),
                "lt": params["lt"],
                "execution": params["execution"],
                "_eventId": "submit",
            }
            cas_login_url = "{}?service={}".format(
                self.sso_url, urllib.parse.quote(service_url, safe=''))
            _, cas_location = self._make_request_no_redirect(
                cas_login_url, data=login_data,
                headers={"Referer": cas_login_url,
                          "Content-Type": "application/x-www-form-urlencoded"},
            )
            redirect_back = cas_location or ""
            ticket_m = re.search(r"ticket=([^&\s]+)", redirect_back)
            if not ticket_m:
                if "用户名或密码错误" in redirect_back:
                    return {"success": False, "message": "用户名或密码错误"}
                return {"success": False, "message": "CAS 未返回 ticket: {}".format(redirect_back[:200])}
            ticket = ticket_m.group(1)

            # 步骤 3: 带 ticket 调用 IPGW API 完成登录
            api_path = "/v1/srun_portal_sso?ac_id={}&ticket={}".format(DEFAULT_AC_ID, ticket)
            st3, body3, _, _ = self._ipgw_raw_request(
                "GET", api_path,
                extra_headers={
                    "Referer": service_url,
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                })
            self._save_debug("sso_login_result.json", body3)

            try:
                result = json.loads(body3)
            except ValueError:
                return {"success": False, "message": "API 非 JSON: {}".format(body3[:200])}

            if result.get("error") == "ok" or result.get("code") == 0:
                return {"success": True, "message": "登录成功"}
            if result.get("Redirect"):
                return {"success": True, "message": "登录成功（已重定向）"}

            return {
                "success": False,
                "message": result.get("message") or result.get("error") or "登录失败",
                "raw": result,
            }
        except Exception as e:
            return {"success": False, "message": "登录异常: {}".format(str(e))}

    def _get_srun_ip(self):
        """从 rad_user_info 获取客户端 IP"""
        cb = "srun_ip_{}_{}".format(int(time.time() * 1000), 1)
        url = "{}/cgi-bin/rad_user_info?callback={}&_={}".format(
            self.portal_url, cb, int(time.time() * 1000) + 1)
        resp = self._make_request(url)
        info = _parse_jsonp(resp)
        return info.get("online_ip") or info.get("client_ip", "")

    def _get_srun_challenge(self, username, ip):
        """获取 srun challenge token"""
        params = urllib.parse.urlencode({
            "callback": "srun_challenge",
            "username": username,
            "ip": ip,
            "_": str(int(time.time() * 1000)),
        })
        url = "{}/cgi-bin/get_challenge?{}".format(self.portal_url, params)
        resp = self._make_request(url)
        info = _parse_jsonp(resp)
        return info.get("challenge", "")

    def login_srun(self, username, password):
        """使用 srun 门户原生协议登录（无需 CAS/mysession）"""
        ac_id = DEFAULT_AC_ID

        ip = self._get_srun_ip()
        if not ip:
            return {"success": False, "message": "无法获取客户端 IP"}

        token = self._get_srun_challenge(username, ip)
        if not token:
            return {"success": False, "message": "无法获取 challenge token"}

        hmd5 = hmac.new(token.encode('ascii'), password.encode('utf-8'), hashlib.md5).hexdigest()

        info_obj = {
            "username": username,
            "password": password,
            "ip": ip,
            "acid": ac_id,
            "enc_ver": "srun_bx1",
        }
        info_json = json.dumps(info_obj, separators=(',', ':'))
        encoded_info = "{SRBX1}" + _srun_base64(_srun_xencode(info_json, token))

        chksum_str = (token + username + token + hmd5 + token + ac_id
                      + token + ip + token + "200" + token + "1"
                      + token + encoded_info)
        chksum = hashlib.sha1(chksum_str.encode('utf-8')).hexdigest()

        params = urllib.parse.urlencode({
            "callback": "srun_portal",
            "action": "login",
            "username": username,
            "password": "{MD5}" + hmd5,
            "os": "Linux",
            "name": "Linux",
            "double_stack": "0",
            "chksum": chksum,
            "info": encoded_info,
            "ac_id": ac_id,
            "ip": ip,
            "n": "200",
            "type": "1",
            "_": str(int(time.time() * 1000)),
        })
        url = "{}/cgi-bin/srun_portal?{}".format(self.portal_url, params)
        resp = self._make_request(url)
        self._save_debug("srun_portal_login.json", resp)
        result = _parse_jsonp(resp)

        if result.get("error") == "ok" or result.get("res") == "ok":
            return {
                "success": True,
                "message": "登录成功",
                "ip": result.get("online_ip") or result.get("client_ip", ""),
                "username": result.get("username", username),
            }
        err_msg = result.get("error_msg") or result.get("error") or "登录失败"
        return {"success": False, "message": err_msg, "raw": result}

    def logout(self):
        """登出网关"""
        callback = "srun_portal_{}".format(int(time.time() * 1000))
        logout_url = "{}/cgi-bin/srun_portal?callback={}&action=logout&ac_id={}&_={}".format(
            self.portal_url, callback, DEFAULT_AC_ID, int(time.time() * 1000) + 1)
        response = self._make_request(logout_url)
        result = _parse_jsonp(response)
        if result.get('error') == 'ok' or result.get('res') == 'ok':
            return {"success": True, "message": "登出成功"}
        return {"success": False, "message": result.get('error_msg') or result.get('error') or '登出失败'}

    def get_status(self):
        """获取当前状态（请求头与浏览器一致，便于网关识别）"""
        callback = "jQuery_{}_{}".format(int(time.time() * 1000), int(time.time() * 1000))
        status_url = "{}/cgi-bin/rad_user_info?callback={}&_={}".format(
            self.portal_url, callback, int(time.time() * 1000) + 1
        )
        headers = {
            "Accept": "text/javascript, application/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.portal_url + "/",
        }
        response = self._make_request(status_url, headers=headers)
        self._save_debug("rad_user_info_raw.txt", response)

        json_str = response.strip()
        # 若为 JSONP（如 jQuery123_123(...)），则取括号内 JSON
        if "(" in json_str and ")" in json_str:
            match = re.search(r"\((\{.*\})\)\s*;?\s*$", json_str, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                # 退化为取第一个 { 到最后一个 } 之间的内容
                start = json_str.find("{")
                end = json_str.rfind("}")
                if start != -1 and end != -1 and end > start:
                    json_str = json_str[start : end + 1]
        # 若明显是 HTML，直接给出提示
        if json_str.lstrip().startswith("<") or "<!DOCTYPE" in json_str or "<html" in json_str.lower():
            return {
                "success": False,
                "message": "获取状态失败，网关返回了 HTML（可能未登录或需在浏览器中打开网关页）。详见 debug/rad_user_info_raw.txt",
            }
        try:
            info = json.loads(json_str)
            if info.get("error") == "ok":
                return {
                    "success": True,
                    "online": True,
                    "username": info.get("user_name", ""),
                    "ip": info.get("online_ip", ""),
                    "bytes_in": info.get("bytes_in", 0),
                    "bytes_out": info.get("bytes_out", 0),
                }
            # 网关明确返回未在线（如 not_online_error），给出原因说明
            err = info.get("error") or info.get("res") or ""
            err_msg = info.get("error_msg") or ""
            if err == "not_online_error" or "not_online" in err:
                return {"success": True, "online": False, "message": "未在线"}
            return {"success": True, "online": False, "message": err_msg or "当前未登录"}
        except ValueError:
            snippet = (json_str[:300] + "..." if len(json_str) > 300 else json_str).replace("\n", " ")
            return {
                "success": False,
                "message": "获取状态失败，响应格式错误。内容预览: {}".format(snippet),
            }


def main():
    """主函数"""
    gateway = NEUGateway()
    current_username = DEFAULT_USERNAME
    current_password = DEFAULT_PASSWORD

    while True:
        print("\n东北大学网关管理")
        print("当前帐号: {}".format(current_username))
        print("1. 登录")
        print("2. 登出")
        print("3. 查看状态")
        print("4. 更换帐号")
        print("5. 退出")
        choice = input("请选择操作 (1-5): ").strip()

        if choice == "1":
            result = gateway.login(current_username, current_password)
            print(result["message"])
            if result.get("raw"):
                print("详情: {}".format(result["raw"]))

        elif choice == "2":
            result = gateway.logout()
            print(result["message"])

        elif choice == "3":
            status = gateway.get_status()
            if status["success"]:
                if status.get("online", False):
                    print("当前状态: 在线")
                    print("用户名: {}".format(status["username"]))
                    print("IP地址: {}".format(status["ip"]))
                    print("上传流量: {:.2f} MB".format(status["bytes_out"] / 1024 / 1024))
                    print("下载流量: {:.2f} MB".format(status["bytes_in"] / 1024 / 1024))
                else:
                    print("当前状态: 离线")
                    if status.get("reason"):
                        print(status["reason"])
            else:
                print("获取状态失败: {}".format(status["message"]))

        elif choice == "4":
            new_username = input("请输入新学号: ").strip()
            new_password = input("请输入新密码: ").strip()
            if new_username and new_password:
                current_username = new_username
                current_password = new_password
                print("已更换为帐号: {}".format(current_username))
            else:
                print("学号或密码不能为空，未更换。")

        elif choice == "5":
            print("感谢使用！")
            break

        else:
            print("无效的选择，请重试")


if __name__ == "__main__":
    # 直接运行脚本 = 用默认账号登录并退出；加 -i/--interactive 进入菜单
    if len(sys.argv) > 1 and sys.argv[1] in ("-i", "--interactive"):
        main()
    else:
        gateway = NEUGateway()
        result = gateway.login(DEFAULT_USERNAME, DEFAULT_PASSWORD)
        print(result["message"])
        for line in result.get("steps", []):
            print(line)
        if result.get("raw"):
            print("详情: {}".format(result["raw"]))
        if result.get("success"):
            status = gateway.get_status()
            if status.get("success") and status.get("online"):
                print("当前状态: 已在线")
                print("用户: {}  IP: {}".format(status.get("username", ""), status.get("ip", "")))
            else:
                print("当前状态: 未在线")
        sys.exit(0 if result.get("success") else 1)