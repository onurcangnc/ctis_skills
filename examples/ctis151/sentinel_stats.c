#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

enum { LINE_CAPACITY = 64, MIN_SCORE = 0, MAX_SCORE = 100 };

static int parse_score(const char *text, int *score) {
    char *end = NULL;
    long value;

    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || (*end != '\n' && *end != '\0')) {
        return 0;
    }
    if (value < -1 || value > MAX_SCORE) {
        return 0;
    }
    *score = (int)value;
    return 1;
}

int main(void) {
    char line[LINE_CAPACITY];
    int count = 0;
    int total = 0;

    while (fgets(line, sizeof line, stdin) != NULL) {
        int score = 0;
        if (!parse_score(line, &score)) {
            puts("INVALID");
            continue;
        }
        if (score == -1) {
            break;
        }
        total += score;
        count += 1;
    }

    if (count == 0) {
        puts("COUNT 0");
    } else {
        printf("COUNT %d AVERAGE %.2f\n", count, (double)total / count);
    }
    return 0;
}
