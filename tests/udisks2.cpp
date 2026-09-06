// SPDX-License-Identifier: Apache-2.0
#include "flatpak-udisks2.h"
#include <QCoreApplication>
#include <QTemporaryFile>
#include <cstdlib>

static void check(bool ok, const char *message) {
    if (!ok) {
        qCritical() << message;
        std::exit(1);
    }
}

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    using namespace FlatpakUDisks;
    check(qEnvironmentVariable("RPI_IMAGER_MOCK_UDISKS") == "1", "Mock bus required");
    Objects objects;
    check(getObjects(objects), "GetManagedObjects could not be decoded");
    const QString disk = "/org/freedesktop/UDisks2/block_devices/mmcblk1";
    check(findDevice(objects, 101) == disk, "DeviceNumber lookup failed");
    check(findDevice(objects, 999).isEmpty(), "Unknown device accepted");
    check(!belongsToDevice(disk + "0", objects.value(QDBusObjectPath(disk + "0")), disk),
          "Device prefix collision accepted");
    check(unmountObjects(objects, disk), "Partition unmount or NotMounted handling failed");
    QDBusReply<QStringList> calls = call("/test", "org.example.Test", "Calls");
    check(calls.isValid() && calls.value().size() == 2 &&
          calls.value().contains(disk + "p1") && calls.value().contains(disk + "p2"),
          "Unmount touched unrelated devices or missed partitions");
    check(!unmountObjects(objects, disk + "0"), "Busy filesystem failure ignored");

    int fd = openObject(disk, O_RDWR | O_EXCL);
    check(fd >= 0, "Authorized descriptor missing");
    check(fcntl(fd, F_GETFD) & FD_CLOEXEC, "Descriptor leaks across exec");
    char byte = 0;
    check(read(fd, &byte, 1) == 1 && byte == 'x', "Descriptor expired with D-Bus reply");
    close(fd);
    check(openObject(disk + "0", O_RDWR | O_EXCL) < 0 && errno == ECANCELED,
          "Authorization cancellation must stop retries");
    QTemporaryFile file;
    check(file.open(), "Temporary file unavailable");
    check(unmountDevice(file.fileName()), "Regular output file should need no unmount");
    check(openDevice(file.fileName().toUtf8(), O_RDWR) < 0 && errno == ENOTBLK,
          "Regular file passed to privileged block-device API");
    qInfo() << "UDisks2 regression checks passed";
}
