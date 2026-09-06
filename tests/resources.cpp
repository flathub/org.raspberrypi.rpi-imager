// SPDX-License-Identifier: Apache-2.0
// Test the resources registered by the actual application executable.
// Intercept main only in the test process, after static Qt resource initializers.
#include <QCoreApplication>
#include <QFile>
#include <QStringList>
#include <cstdio>
#include <dlfcn.h>

namespace {
int checkResources(int argc, char **argv, char **) {
    QCoreApplication app(argc, argv);
    QFile file(":/timezones.txt");
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        std::fprintf(stderr, "Missing packaged resource: :/timezones.txt\n");
        return 1;
    }
    const auto zones = QString::fromUtf8(file.readAll()).split('\n', Qt::SkipEmptyParts);
    if (zones.size() < 100 || !zones.contains("Europe/London") ||
        !zones.contains("America/New_York") || !zones.contains("Asia/Tokyo")) {
        std::fprintf(stderr, "Packaged time-zone list is incomplete\n");
        return 1;
    }
    std::printf("Packaged time-zone resource passed: %lld zones, including Europe/London\n",
                static_cast<long long>(zones.size()));
    return 0;
}
}

extern "C" int __libc_start_main(int (*)(int, char **, char **), int argc,
                                 char **argv, void (*init)(), void (*fini)(),
                                 void (*rtldFini)(), void *stackEnd) {
    using StartMain = int (*)(int (*)(int, char **, char **), int, char **,
                              void (*)(), void (*)(), void (*)(), void *);
    auto startMain = reinterpret_cast<StartMain>(dlsym(RTLD_NEXT, "__libc_start_main"));
    if (!startMain)
        return 1;
    return startMain(checkResources, argc, argv, init, fini, rtldFini, stackEnd);
}
