#pragma once
extern int test_warnings;
#define LOG_WARNING(...) (++test_warnings)
