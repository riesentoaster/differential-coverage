#include <stdio.h>
#include <stdlib.h>

static int add(int a, int b) { return a + b; }

static int sub(int a, int b) { return a - b; }

static int mul(int a, int b) { return a * b; }

static int div_op(int a, int b) {
    if (b == 0) {
        return 0;
    }
    return a / b;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        return 1;
    }

    char op = argv[1][0];
    int a = atoi(argv[2]);
    int b = atoi(argv[3]);
    int result = 0;

    switch (op) {
    case 'a':
        result = add(a, b);
        break;
    case 's':
        result = sub(a, b);
        break;
    case 'm':
        result = mul(a, b);
        break;
    case 'd':
        result = div_op(a, b);
        break;
    default:
        return 2;
    }

    printf("%d\n", result);
    return 0;
}
