#include <stddef.h>
#include <stdio.h>

static int add(int a, int b) { return a + b; }

static int sub(int a, int b) { return a - b; }

static int mul(int a, int b) { return a * b; }

static int div_op(int a, int b) {
    if (b == 0) {
        return 0;
    }
    return a / b;
}

static int run_op(char op, int a, int b) {
    switch (op) {
    case 'a':
        return add(a, b);
    case 's':
        return sub(a, b);
    case 'm':
        return mul(a, b);
    case 'd':
        return div_op(a, b);
    default:
        return -1;
    }
}

#ifdef __cplusplus
extern "C"
#endif
int LLVMFuzzerTestOneInput(const unsigned char *data, size_t size) {
    FILE *in = fmemopen((void *)data, size, "r");
    if (!in) {
        return 0;
    }
    char op = 0;
    int a = 0;
    int b = 0;
    int matched = fscanf(in, " %c %d %d", &op, &a, &b);
    fclose(in);
    if (matched != 3) {
        return 0;
    }
    (void)run_op(op, a, b);
    return 0;
}

#ifndef FUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION
int main(void) {
    unsigned char buf[64];
    LLVMFuzzerTestOneInput(buf, fread(buf, 1, sizeof(buf), stdin));
    return 0;
}
#endif
