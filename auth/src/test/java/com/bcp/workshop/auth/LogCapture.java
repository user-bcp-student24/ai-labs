package com.bcp.workshop.auth;

import java.util.logging.Handler;
import java.util.logging.LogRecord;
import java.util.logging.Logger;

final class LogCapture {
    private static final StringBuilder OUTPUT = new StringBuilder();
    private static boolean installed;

    private LogCapture() {}

    static synchronized void install() {
        if (installed) {
            return;
        }
        installed = true;
        Logger.getLogger("").addHandler(new Handler() {
            @Override
            public void publish(LogRecord record) {
                synchronized (OUTPUT) {
                    OUTPUT.append(record.getMessage()).append('\n');
                    if (record.getThrown() != null) {
                        OUTPUT.append(record.getThrown()).append('\n');
                    }
                }
            }

            @Override
            public void flush() {}

            @Override
            public void close() {}
        });
    }

    static String content() {
        synchronized (OUTPUT) {
            return OUTPUT.toString();
        }
    }
}
