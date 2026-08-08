/*
 * Process Monitor - CPU and Memory Usage Monitor
 * 
 * Author: JeffreySharp
 * Encoding: UTF-8
 * 
 * Usage: ./monitor_process [CPU_threshold%] [Memory_threshold] [interval_seconds]
 * Memory unit: pure number=MB, suffix G=GB, suffix MB=MB
 * Example: ./monitor_process 80 2G 60     # CPU 80%, Memory 2GB, check every 60s
 *          ./monitor_process 50 500 30    # CPU 50%, Memory 500MB, check every 30s
 *          ./monitor_process 50 500MB 10  # CPU 50%, Memory 500MB, check every 10s
 *          ./monitor_process              # Use defaults: CPU 50%, Memory 1GB, check every 30s
 * 
 * Features:
 * - Monitors processes exceeding CPU/Memory thresholds
 * - Displays alerts in terminal top-right corner as table
 * - No repeated alerts within 10 minutes for same process
 * - Optimized scanning: only monitors processes using >30% of memory threshold
 * - Auto-adapts to terminal width
 * - Kill with: kill <PID>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <unistd.h>
#include <time.h>
#include <ctype.h>
#include <sys/ioctl.h>
#include <termios.h>
#include <signal.h>

// 报警记录结构，用于动态监控
#define MAX_RECORDS 1024
typedef struct {
    int pid;
    char cmd[64];
    int cpu_usage;
    unsigned long mem_kb;
    int display_row;  // 在终端中的显示行号
    time_t last_update;  // 最后更新时间
} AlertRecord;

AlertRecord alert_history[MAX_RECORDS];
int alert_count = 0;
int last_display_row = 1;  // 上次显示到的最大行号（从1开始，1是表头）
int cleanup_needed = 0;    // 标记是否需要清理显示

// 进程信息结构
typedef struct {
    int pid;
    char cmd[64];  // 缩小到64字节，足够显示进程名
    int cpu_usage;  // CPU使用率（整数，单位：%）
    unsigned long mem_kb;  // 内存使用量（KB）
} ProcessInfo;

// CPU统计信息
typedef struct {
    unsigned long user;
    unsigned long nice;
    unsigned long system;
    unsigned long idle;
    unsigned long iowait;
    unsigned long irq;
    unsigned long softirq;
} CpuStat;

// 读取系统总CPU时间
int read_cpu_stat(CpuStat *cpu) {
    FILE *fp = fopen("/proc/stat", "r");
    if (!fp) return -1;
    
    char line[256];
    if (fgets(line, sizeof(line), fp)) {
        sscanf(line, "cpu %lu %lu %lu %lu %lu %lu %lu",
               &cpu->user, &cpu->nice, &cpu->system, &cpu->idle,
               &cpu->iowait, &cpu->irq, &cpu->softirq);
    }
    fclose(fp);
    return 0;
}

// 读取进程的CPU时间
int read_process_stat(int pid, unsigned long *utime, unsigned long *stime) {
    char path[256];
    snprintf(path, sizeof(path), "/proc/%d/stat", pid);
    
    FILE *fp = fopen(path, "r");
    if (!fp) return -1;
    
    char buffer[2048];
    if (!fgets(buffer, sizeof(buffer), fp)) {
        fclose(fp);
        return -1;
    }
    fclose(fp);
    
    // 解析stat文件，格式比较复杂因为cmd可能包含空格和括号
    char *p = strchr(buffer, ')');
    if (!p) return -1;
    p += 2;  // 跳过 ") "
    
    // 跳到第13和14个字段（utime和stime）
    int field = 3;
    while (field < 13 && *p) {
        while (*p && *p != ' ') p++;
        while (*p && *p == ' ') p++;
        field++;
    }
    
    if (sscanf(p, "%lu %lu", utime, stime) != 2) {
        return -1;
    }
    
    return 0;
}

// 读取进程内存使用量（KB）
unsigned long read_process_memory(int pid) {
    char path[256];
    snprintf(path, sizeof(path), "/proc/%d/status", pid);
    
    FILE *fp = fopen(path, "r");
    if (!fp) return 0;
    
    char line[256];
    unsigned long mem_kb = 0;
    
    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "VmRSS:", 6) == 0) {
            sscanf(line + 6, "%lu", &mem_kb);
            break;
        }
    }
    fclose(fp);
    return mem_kb;
}

// 读取进程程序名（只取程序名，不要参数）
void read_process_name(int pid, char *name, size_t size) {
    char path[256];
    snprintf(path, sizeof(path), "/proc/%d/comm", pid);
    
    FILE *fp = fopen(path, "r");
    if (!fp) {
        snprintf(name, size, "[unknown]");
        return;
    }
    
    if (fgets(name, size, fp)) {
        name[strcspn(name, "\n")] = 0;
    } else {
        snprintf(name, size, "[unknown]");
    }
    fclose(fp);
}

// 检查进程是否值得监控（过滤掉内核线程和明显低资源的进程）
int is_worth_monitoring(unsigned long mem_kb, int mem_threshold_mb) {
    // 内存使用量小于阈值30%的进程，认为不太可能超标
    int mem_mb = mem_kb / 1024;
    if (mem_mb < mem_threshold_mb * 30 / 100) {
        return 0;
    }
    return 1;
}

// 查找已存在的报警记录
int find_alert_record(int pid) {
    for (int i = 0; i < alert_count; i++) {
        if (alert_history[i].pid == pid) {
            return i;
        }
    }
    return -1;  // 未找到
}

// 前向声明
int get_terminal_columns();
void print_alert(int pid, const char* cmd, int cpu_usage, unsigned long mem_kb, int cpu_threshold, double mem_threshold_gb, int row);

// 清除过期的报警记录（超过10分钟未更新）
void cleanup_expired_alerts() {
    time_t now = time(NULL);
    int write_idx = 0;
    
    for (int i = 0; i < alert_count; i++) {
        if (now - alert_history[i].last_update < 600) {  // 10分钟内更新过
            if (write_idx != i) {
                alert_history[write_idx] = alert_history[i];
            }
            write_idx++;
        }
    }
    alert_count = write_idx;
}

// 清除从指定行到上次显示的最大行的所有内容
void clear_display_area(int from_row, int to_row) {
    int term_cols = get_terminal_columns();
    int start_col = term_cols - 37;
    if (start_col < 1) start_col = 1;
    
    for (int row = from_row; row <= to_row; row++) {
        printf("\033[s");  // 保存光标位置
        printf("\033[%d;%dH", row, start_col);  // 移动到指定位置
        printf("\033[K");  // 清除从光标到行尾的内容
        printf("\033[u");  // 恢复光标位置
    }
    fflush(stdout);
}

// 完全刷新显示区域
void refresh_display_area(int cpu_threshold, double mem_threshold_gb) {
    // 1. 先清除上次显示的所有内容（从表头到最后一行）
    clear_display_area(1, last_display_row);
    
    // 2. 重置显示行计数器
    int current_row = 1;
    
    // 3. 打印表头
    int term_cols = get_terminal_columns();
    int start_col = term_cols - 37;
    if (start_col < 1) start_col = 1;
    
    printf("\033[s");  // 保存光标位置
    printf("\033[%d;%dH", current_row, start_col);  // 移动到第1行
    printf("\033[1;37m%-7s %-12s %6s %7s\033[0m", "PID", "PROGRAM", "CPU%", "MEM(G)");
    printf("\033[u");  // 恢复光标位置
    current_row++;
    
    // 4. 打印所有当前超标的进程
    for (int i = 0; i < alert_count; i++) {
        AlertRecord *record = &alert_history[i];
        
        // 更新显示行号
        record->display_row = current_row;
        
        // 打印进程信息
        print_alert(record->pid, record->cmd, record->cpu_usage, record->mem_kb, 
                   cpu_threshold, mem_threshold_gb, current_row);
        current_row++;
    }
    
    // 5. 更新最后显示行号
    last_display_row = current_row - 1;
    
    fflush(stdout);
}

// 添加或更新报警记录（简化版本，只更新数据，不管理显示）
void update_alert_record(int pid, const char* cmd, int cpu_usage, unsigned long mem_kb) {
    int idx = find_alert_record(pid);
    time_t now = time(NULL);
    
    if (idx >= 0) {
        // 更新已存在的记录
        alert_history[idx].cpu_usage = cpu_usage;
        alert_history[idx].mem_kb = mem_kb;
        alert_history[idx].last_update = now;
        strncpy(alert_history[idx].cmd, cmd, sizeof(alert_history[idx].cmd) - 1);
        alert_history[idx].cmd[sizeof(alert_history[idx].cmd) - 1] = '\0';
    } else {
        // 添加新记录
        if (alert_count < MAX_RECORDS) {
            alert_history[alert_count].pid = pid;
            alert_history[alert_count].cpu_usage = cpu_usage;
            alert_history[alert_count].mem_kb = mem_kb;
            alert_history[alert_count].last_update = now;
            strncpy(alert_history[alert_count].cmd, cmd, sizeof(alert_history[alert_count].cmd) - 1);
            alert_history[alert_count].cmd[sizeof(alert_history[alert_count].cmd) - 1] = '\0';
            alert_count++;
        }
    }
}

// 获取终端列数
int get_terminal_columns() {
    struct winsize w;
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &w) == -1) {
        return 80;  // 如果获取失败，默认返回80列
    }
    return w.ws_col;
}

// 获取ANSI颜色代码
const char* get_color_code(int cpu, double mem_gb, int cpu_threshold, double mem_threshold) {
    double cpu_ratio = (double)cpu / cpu_threshold;
    double mem_ratio = mem_gb / mem_threshold;
    double max_ratio = cpu_ratio > mem_ratio ? cpu_ratio : mem_ratio;
    
    if (max_ratio >= 2.0) return "\033[91m";      // 亮红色
    if (max_ratio >= 1.5) return "\033[31m";      // 红色
    if (max_ratio >= 1.2) return "\033[93m";      // 亮黄色
    return "\033[33m";                             // 黄色
}

// 打印报警信息到终端右上角（表格形式）
void print_alert(int pid, const char* cmd, int cpu_usage, unsigned long mem_kb, int cpu_threshold, double mem_threshold_gb, int row) {
    double mem_gb = mem_kb / 1024.0 / 1024.0;
    const char *color = get_color_code(cpu_usage, mem_gb, cpu_threshold, mem_threshold_gb);
    
    // 截取程序名的开头12个字符
    char short_name[70];  // 增大缓冲区避免truncation警告
    size_t name_len = strlen(cmd);
    if (name_len > 12) {
        snprintf(short_name, sizeof(short_name), "%.9s...", cmd);
    } else {
        snprintf(short_name, sizeof(short_name), "%s", cmd);
    }
    
    // 动态计算列位置（与表头对齐）
    int term_cols = get_terminal_columns();
    int start_col = term_cols - 37;  // 留2列边距
    if (start_col < 1) start_col = 1;
    
    // 保存光标位置，移动到目标位置，打印数据，恢复光标位置
    printf("\033[s");  // 保存光标位置
    printf("\033[%d;%dH", row, start_col);  // 移动到第row行，start_col列
    printf("%s%-7d %-12s %6d %7.2f\033[0m", color, pid, short_name, cpu_usage, mem_gb);
    printf("\033[u");  // 恢复光标位置
    fflush(stdout);
}

// 清除所有显示的内容
void clear_all_displays() {
    if (!cleanup_needed) return;
    
    // 清除从第1行到最后显示行的所有内容
    clear_display_area(1, last_display_row);
    
    // 恢复光标位置
    printf("\033[?25h");  // 显示光标
    fflush(stdout);
    
    // printf("\nMonitor stopped. All displays cleared.\n");
}

// 信号处理函数
void signal_handler(int sig) {
    switch(sig) {
        case SIGTERM:
        case SIGINT:
            clear_all_displays();
            exit(0);
            break;
    }
}

// 扫描进程并检查是否超过阈值（优化版：只扫描可能超标的进程）
void scan_processes(int cpu_threshold, int mem_threshold_mb) {
    DIR *proc_dir = opendir("/proc");
    if (!proc_dir) {
        perror("Failed to open /proc");
        return;
    }
    
    // 第一阶段：快速扫描，筛选出可能超标的进程
    #define MAX_PIDS 4096
    struct {
        int pid;
        unsigned long mem_kb;
        unsigned long utime;
        unsigned long stime;
    } candidate_pids[MAX_PIDS];
    int candidate_count = 0;
    
    struct dirent *entry;
    while ((entry = readdir(proc_dir)) != NULL && candidate_count < MAX_PIDS) {
        if (!isdigit(entry->d_name[0])) continue;
        
        int pid = atoi(entry->d_name);
        
        // 快速读取内存使用量
        unsigned long mem_kb = read_process_memory(pid);
        
        // 跳过明显内存使用量很低的进程（低于阈值30%）
        if (!is_worth_monitoring(mem_kb, mem_threshold_mb)) {
            continue;
        }
        
        // 读取CPU时间
        unsigned long utime, stime;
        if (read_process_stat(pid, &utime, &stime) == 0) {
            candidate_pids[candidate_count].pid = pid;
            candidate_pids[candidate_count].mem_kb = mem_kb;
            candidate_pids[candidate_count].utime = utime;
            candidate_pids[candidate_count].stime = stime;
            candidate_count++;
        }
    }
    closedir(proc_dir);
    
    // 如果没有候选进程，直接返回
    if (candidate_count == 0) return;
    
    // 读取第一次CPU统计
    CpuStat cpu_start;
    read_cpu_stat(&cpu_start);
    unsigned long total_start = cpu_start.user + cpu_start.nice + cpu_start.system + 
                                cpu_start.idle + cpu_start.iowait + cpu_start.irq + cpu_start.softirq;
    
    // 等待一小段时间（100ms）再次采样
    usleep(100000);
    
    // 读取第二次CPU统计
    CpuStat cpu_end;
    read_cpu_stat(&cpu_end);
    unsigned long total_end = cpu_end.user + cpu_end.nice + cpu_end.system + 
                              cpu_end.idle + cpu_end.iowait + cpu_end.irq + cpu_end.softirq;
    unsigned long total_diff = total_end - total_start;
    
    // 第二阶段：对候选进程计算精确的CPU使用率并收集当前超标的进程
    double mem_threshold_gb = mem_threshold_mb / 1024.0;
    
    // 临时存储当前轮次的超标进程
    struct {
        int pid;
        char cmd[64];
        int cpu_usage;
        unsigned long mem_kb;
    } current_alerts[MAX_PIDS];
    int current_alert_count = 0;
    
    for (int i = 0; i < candidate_count; i++) {
        int pid = candidate_pids[i].pid;
        unsigned long mem_kb = candidate_pids[i].mem_kb;
        unsigned long utime, stime;
        
        // 读取第二次CPU时间
        if (read_process_stat(pid, &utime, &stime) != 0) continue;
        
        unsigned long proc_total_start = candidate_pids[i].utime + candidate_pids[i].stime;
        unsigned long proc_total_end = utime + stime;
        unsigned long proc_diff = proc_total_end - proc_total_start;
        
        // 计算CPU使用率
        int cpu_usage = 0;
        if (total_diff > 0) {
            cpu_usage = (int)((100 * proc_diff) / total_diff * sysconf(_SC_NPROCESSORS_ONLN));
        }
        
        int mem_mb = mem_kb / 1024;
        char cmd[64];
        read_process_name(pid, cmd, sizeof(cmd));
        
        // 检查是否超过阈值
        if (cpu_usage > cpu_threshold || mem_mb > mem_threshold_mb) {
            if (current_alert_count < MAX_PIDS) {
                current_alerts[current_alert_count].pid = pid;
                current_alerts[current_alert_count].cpu_usage = cpu_usage;
                current_alerts[current_alert_count].mem_kb = mem_kb;
                strncpy(current_alerts[current_alert_count].cmd, cmd, sizeof(current_alerts[current_alert_count].cmd) - 1);
                current_alerts[current_alert_count].cmd[sizeof(current_alerts[current_alert_count].cmd) - 1] = '\0';
                current_alert_count++;
            }
        }
    }
    
    // 第三阶段：更新报警记录并刷新显示
    if (current_alert_count > 0) {
        cleanup_needed = 1;  // 标记需要清理
        
        // 清空旧的报警记录
        alert_count = 0;
        
        // 添加当前超标的进程到报警记录
        for (int i = 0; i < current_alert_count; i++) {
            update_alert_record(current_alerts[i].pid, current_alerts[i].cmd, 
                               current_alerts[i].cpu_usage, current_alerts[i].mem_kb);
        }
        
        // 完全刷新显示区域
        refresh_display_area(cpu_threshold, mem_threshold_gb);
    } else {
        // 如果没有超标进程，清除显示
        if (cleanup_needed) {
            clear_display_area(1, last_display_row);
            last_display_row = 1;
        }
        alert_count = 0;
    }
    
    // 清理过期的报警记录（保留历史记录用于10分钟去重）
    cleanup_expired_alerts();
}

// 解析内存参数（支持MB和G）
int parse_memory_arg(const char *arg) {
    double value = atof(arg);
    size_t len = strlen(arg);
    
    // 检查是否以G或g结尾（表示GB）
    if (len >= 1 && (arg[len-1] == 'G' || arg[len-1] == 'g')) {
        return (int)(value * 1024.0);  // G转换为MB
    }
    
    // 检查是否以MB结尾
    if (len >= 2 && (arg[len-2] == 'M' || arg[len-2] == 'm') && 
        (arg[len-1] == 'B' || arg[len-1] == 'b')) {
        return (int)value;  // 返回MB
    }
    
    // 纯数字默认当作MB
    return (int)value;
}

int main(int argc, char *argv[]) {
    int default_cpu_threshold = 50;
    int default_mem_threshold = 1024;  // 1GB = 1024MB
    int default_interval = 30;  // 30秒默认间隔
    
    int cpu_threshold, mem_threshold_mb, interval_seconds;
    
    if (argc < 3) {
        // 使用默认值
        cpu_threshold = default_cpu_threshold;
        mem_threshold_mb = default_mem_threshold;
        interval_seconds = default_interval;
    } else if (argc < 4) {
        // 只有CPU和内存阈值
        cpu_threshold = atoi(argv[1]);
        mem_threshold_mb = parse_memory_arg(argv[2]);
        interval_seconds = default_interval;
    } else {
        // 三个参数都有
        cpu_threshold = atoi(argv[1]);
        mem_threshold_mb = parse_memory_arg(argv[2]);
        interval_seconds = atoi(argv[3]);
    }
    
    // 设置信号处理
    signal(SIGTERM, signal_handler);  // kill命令
    signal(SIGINT, signal_handler);   // Ctrl+C
    
    // 简洁输出：只打印一行关键信息，智能显示单位
    if (mem_threshold_mb >= 1024) {
        printf("Monitor[PID:%d] CPU>%d%% MEM>%.1fG | Check interval: %ds | Kill: kill %d\n",
               getpid(), cpu_threshold, mem_threshold_mb / 1024.0, interval_seconds, getpid());
    } else {
        printf("Monitor[PID:%d] CPU>%d%% MEM>%dMB | Check interval: %ds | Kill: kill %d\n",
               getpid(), cpu_threshold, mem_threshold_mb, interval_seconds, getpid());
    }
    
    while (1) {
        scan_processes(cpu_threshold, mem_threshold_mb);
        sleep(interval_seconds);  // 使用指定的间隔时间
    }
    
    return 0;
}

