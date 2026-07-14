#include <stdio.h>

#define CHECK(x)                     \
    do {                             \
        if (!(x)) {                  \
            return 1;                \
        }                            \
    } while (0)

int main(void) {
    CHECK(1);
    puts("ok");
    return 0;
}
