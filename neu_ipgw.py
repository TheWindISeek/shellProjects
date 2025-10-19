import urllib.request
import urllib.parse
import urllib.error
import json
import re
import ssl
import http.cookiejar


class NEUGateway:
    """Python 3.6.5 兼容版本的网关类"""
    
    def __init__(self):
        # 创建支持cookie的opener
        self.cookie_jar = http.cookiejar.CookieJar()
        
        # 创建一个忽略SSL证书验证的上下文
        context = ssl._create_unverified_context()
        
        # 创建支持HTTPS的处理器
        https_handler = urllib.request.HTTPSHandler(context=context)
        
        # 创建opener，包含cookie处理器和HTTPS处理器
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            https_handler
        )
        
        # 基础URL
        self.sso_url = "https://pass.neu.edu.cn/tpass/login"
        self.portal_url = "http://ipgw.neu.edu.cn"
        
        # 设置基础请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def _make_request(self, url, data=None, headers=None):
        """发送HTTP请求并返回响应内容"""
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
                return response.read().decode('utf-8')
        except urllib.error.URLError as e:
            raise Exception("请求失败: {}".format(str(e)))

    def _get_lt_token(self):
        """获取登录所需的lt token"""
        service_param = urllib.parse.quote("{}".format(self.portal_url) + "/srun_portal_sso?ac_id=1")
        sso_url_with_service = "{}?service={}".format(self.sso_url, service_param)
        
        response = self._make_request(sso_url_with_service)
        lt_match = re.search(r'name="lt" value="(.*?)"', response)
        if not lt_match:
            raise Exception("无法获取lt token")
        return lt_match.group(1)

    def login(self, username, password):
        """登录网关"""
        try:
            # 获取lt token
            lt = self._get_lt_token()
            
            # 准备登录数据
            login_data = {
                'rsa': username + password + lt,
                'ul': len(username),
                'pl': len(password),
                'lt': lt,
                'execution': 'e1s1',
                '_eventId': 'submit'
            }

            # 发送登录请求
            service_param = urllib.parse.quote("{}".format(self.portal_url) + "/srun_portal_sso?ac_id=1")
            login_url = "{}?service={}".format(self.sso_url, service_param)
            response = self._make_request(login_url, login_data)

            # 从响应中提取ticket
            if "IP控制网关" in response:
                # 获取当前URL中的ticket参数
                try:
                    req = urllib.request.Request(login_url)
                    response_obj = self.opener.open(req)
                    current_url = response_obj.geturl()
                    ticket_match = re.search(r'ticket=([^&]+)', current_url)
                    if ticket_match:
                        ticket = ticket_match.group(1)
                        # 使用ticket进行实际的网关登录
                        portal_login_url = "{}/v1/srun_portal_sso?ac_id=1&ticket={}".format(self.portal_url, ticket)
                        portal_response = self._make_request(portal_login_url)
                        
                        try:
                            portal_result = json.loads(portal_response)
                            if portal_result.get('error') == 'ok' or portal_result.get('code') == 0:
                                return {"success": True, "message": "登录成功"}
                            else:
                                return {"success": False, "message": portal_result.get('message', '登录失败')}
                        except ValueError:  # json.JSONDecodeError 的 Python 3.6 兼容写法
                            return {"success": False, "message": "登录响应解析失败"}
                    else:
                        return {"success": False, "message": "无法获取登录凭证"}
                except Exception:
                    return {"success": False, "message": "无法获取登录凭证"}
            elif "用户名或密码错误" in response:
                return {"success": False, "message": "用户名或密码错误"}
            else:
                return {"success": False, "message": "登录失败，未知错误"}
        except Exception as e:
            return {"success": False, "message": "登录异常: {}".format(str(e))}

    def logout(self):
        """登出网关"""
        logout_url = "{}/cgi-bin/srun_portal?action=logout".format(self.portal_url)
        response = self._make_request(logout_url)
        
        try:
            result = json.loads(response)
            if result.get('error') == 'ok':
                return {"success": True, "message": "登出成功"}
            else:
                return {"success": False, "message": result.get('error_msg', '登出失败')}
        except ValueError:  # json.JSONDecodeError 的 Python 3.6 兼容写法
            return {"success": False, "message": "登出失败，响应格式错误"}

    def get_status(self):
        """获取当前状态"""
        status_url = "{}/cgi-bin/rad_user_info".format(self.portal_url)
        response = self._make_request(status_url)
        
        try:
            info = json.loads(response)
            if info.get('error') == 'ok':
                return {
                    "success": True,
                    "online": True,
                    "username": info.get('user_name', ''),
                    "ip": info.get('online_ip', ''),
                    "bytes_in": info.get('bytes_in', 0),
                    "bytes_out": info.get('bytes_out', 0)
                }
            else:
                return {"success": True, "online": False, "message": "当前未登录"}
        except ValueError:  # json.JSONDecodeError 的 Python 3.6 兼容写法
            return {"success": False, "message": "获取状态失败，响应格式错误"}


def main():
    """主函数"""
    gateway = NEUGateway()
    
    while True:
        print("\n东北大学网关管理")
        print("1. 登录")
        print("2. 登出")
        print("3. 查看状态")
        print("4. 退出")
        
        choice = input("请选择操作 (1-4): ")
        
        if choice == '1':
            username = input("请输入学号: ")
            password = input("请输入密码: ")
            result = gateway.login(username, password)
            print(result['message'])
        
        elif choice == '2':
            result = gateway.logout()
            print(result['message'])
        
        elif choice == '3':
            status = gateway.get_status()
            if status['success']:
                if status.get('online', False):
                    print("当前状态: 在线")
                    print("用户名: {}".format(status['username']))
                    print("IP地址: {}".format(status['ip']))
                    print("上传流量: {:.2f} MB".format(status['bytes_out']/1024/1024))
                    print("下载流量: {:.2f} MB".format(status['bytes_in']/1024/1024))
                else:
                    print("当前状态: 离线")
            else:
                print("获取状态失败: {}".format(status['message']))
        
        elif choice == '4':
            print("感谢使用！")
            break
        
        else:
            print("无效的选择，请重试")


if __name__ == "__main__":
    main()