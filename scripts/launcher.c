/*
 * Live Translator — native macOS launcher
 * Runs Resources/launcher.sh as child process, stays alive as parent
 * so macOS identifies this as the .app's main process.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libgen.h>
#include <signal.h>
#include <sys/wait.h>
#include <mach-o/dyld.h>

static pid_t child_pid = 0;

void handle_signal(int sig) {
    if (child_pid > 0) kill(child_pid, sig);
}

int main(int argc, char *argv[]) {
    char exe_path[4096];
    uint32_t size = sizeof(exe_path);
    _NSGetExecutablePath(exe_path, &size);

    char real_path[4096];
    if (!realpath(exe_path, real_path)) strncpy(real_path, exe_path, sizeof(real_path));

    char dir_buf[4096];
    strncpy(dir_buf, real_path, sizeof(dir_buf));
    char *dir = dirname(dir_buf);

    /* launcher.sh is in Resources, not MacOS */
    char script[4096];
    snprintf(script, sizeof(script), "%s/../Resources/launcher.sh", dir);

    child_pid = fork();
    if (child_pid == 0) {
        execl("/bin/bash", "bash", script, NULL);
        perror("exec failed");
        _exit(1);
    }
    if (child_pid < 0) { perror("fork failed"); return 1; }

    signal(SIGTERM, handle_signal);
    signal(SIGINT, handle_signal);
    signal(SIGHUP, handle_signal);

    int status;
    waitpid(child_pid, &status, 0);
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}
