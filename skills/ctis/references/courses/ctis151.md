# CTIS151 — Structured C programming

You are writing C, compiled as C++ under Visual Studio, so the files end in `.cpp` and every program starts with `#define _CRT_SECURE_NO_WARNINGS`. The course grades the structure of the program and the exactness of its output, not just the answer. A program that computes correctly but prints a different layout than the expected run is incomplete.

## Teaching posture

Scaffolded, example-first, no theory detour. Introduce a construct on a working program, explain it line by line, then ask for a controlled change, then ask for a similar problem unaided. Never open with complexity classes or Big-O; this course does not use them. Every claim about the program is settled by running it and comparing against the expected output.

When a student is stuck, do not hand over the finished program. Give the next single line, or the section comment that names what has to happen there, and let them fill it.

## Scope

Variables and types, expressions and operators, formatted input and output, selection, all three loop forms, input validation, menus, modular programming with functions, one- and two-dimensional arrays, parallel arrays, strings, text files, pointers as output parameters, and the Visual Studio build/debug/watch cycle.

## The required shape

Every program follows this skeleton. Keep the order and the comment style.

```c
/* LG4_Q5 -> Reads a 4 digit binary number, converts it to decimal,
   displays the decimal value and the sum of its digits */

#define _CRT_SECURE_NO_WARNINGS

#include <stdio.h>
#include <math.h>

#define MAX_STUDENTS 100
#define DISCOUNT      25

int main(void)
{
    int number,          //input
        decimal,         //output
        digit1, digit2;  //digits

    //Getting the number from the user
    printf("Enter a binary number: ");
    scanf("%d", &number);

    //Finding the digits
    digit1 = number % 10;
    number /= 10;
    digit2 = number % 10;

    //Display the result
    printf("Decimal equivalent : %d\n", decimal);

    return(0);
}
```

Six habits from that skeleton, all of them graded:

1. **A purpose comment on the first line**, naming the lab guide question and what the program does.
2. **`#define _CRT_SECURE_NO_WARNINGS` before the includes**, otherwise `scanf` will not compile here.
3. **Symbolic constants in upper case** for every fixed number. A literal `25` in the body is a magic number; `DISCOUNT` is not.
4. **`int main(void)`**, with the parameter list written out.
5. **A single declaration block with purpose comments** on the right: `//input`, `//output`, `//counter`, `//accumulator`.
6. **Section comments in the body** that name the phase: `//Getting the number from the user`, `//Calculating`, `//Display the result`. Then `return(0);` with the parentheses.

Names are descriptive camelCase: `shortSide`, `longSide`, `totalPayment`, `studentCount`. Single letters are only for loop indices.

## Skeletons

### Read, compute, display

```c
int main(void)
{
    double pounds,      //input - weight in pounds
           kilograms;   //output - weight in kilograms

    //Getting the weight from the user
    printf("Enter weight in pounds: ");
    scanf("%lf", &pounds);

    //Converting
    kilograms = pounds * KG_PER_POUND;

    //Display the result
    printf("Weight in kilograms : %.2f\n", kilograms);

    return(0);
}
```

Match the format specifier to the type: `%d` for `int`, `%f` for `float`, `%lf` for `double` in `scanf` but `%f` in `printf`, `%c` for `char`, `%s` for a string. `%.2f` fixes two decimals; `%%` prints a literal percent sign.

### Input validation loop

Every value read from the user is validated before it is used. The loop reprints the prompt, it does not just complain.

```c
    printf("Enter the penalty article no: ");
    scanf("%d", &choice);

    while (choice < 1 || choice > 4)
    {
        printf("\nYou typed out of range !!\n");
        printf("\nEnter the penalty article no: ");
        scanf("%d", &choice);
    }
```

For a `char` read after a number, put a space in the format string so the pending newline is skipped:

```c
    printf("payment before deadline (y/n)? ");
    scanf(" %c", &choice);
```

### Menu-driven program

The menu is a function, it validates its own input, and it returns the choice. The main loop redisplays it after every operation.

```c
int menu(void)
{
    int choice;

    printf("TRAFFIC PENALTY PAYMENTS\n");
    printf("------------------------\n");
    printf("1. Speed Limit Violation\n");
    printf("2. Red Light Violation\n");
    printf("3. Parking Violation\n");
    printf("4. EXIT\n");

    printf("Enter the penalty article no: ");
    scanf("%d", &choice);

    while (choice < 1 || choice > 4)
    {
        printf("\nYou typed out of range !!\n");
        printf("Enter the penalty article no: ");
        scanf("%d", &choice);
    }

    return(choice);
}

int main(void)
{
    int choice;
    double total = 0;

    choice = menu();

    while (choice != EXIT_CHOICE)
    {
        switch (choice)
        {
            case 1: total += SPEED_LIMIT; break;
            case 2: total += RED_LIGHT;   break;
            case 3: total += PARKING;     break;
        }
        choice = menu();
    }

    printf("\nPenalty totals: %.2f TL\n", total);

    return(0);
}
```

Every `case` ends with `break`. A `switch` on a menu choice always has a `default` or a validated input; here validation lives in `menu()`.

### Gradual modularization

Functions are introduced in three steps, and assignments follow the same progression. Build them in this order.

```c
//Step 1: no parameters
void dispLine(void)
{
    int i;
    for (i = 0; i < 20; i++)
        printf("*");
    printf("\n");
}

//Step 2: parameters
void dispChar(int n, char ch)
{
    int i;
    for (i = 0; i < n; i++)
        printf("%c", ch);
    printf("\n");
}

//Step 3: a function that uses the previous ones
void dispRectangle(int width, int height, char ch)
{
    int row;
    for (row = 0; row < height; row++)
        dispChar(width, ch);
}
```

State the contract of every function in plain English above it, the way the assignments phrase it: "gets the array and its size, computes and returns the index of the maximum element".

### Value-returning function and output parameter

Return a single result. Use a pointer parameter only when the function must produce more than one.

```c
//Computes and returns the average of the first size elements
double calcAverage(int numbers[], int size)
{
    int i, sum = 0;

    for (i = 0; i < size; i++)
        sum += numbers[i];

    return((double)sum / size);
}

//Finds both the minimum value and its index
void findMin(int numbers[], int size, int *minValue, int *minIndex)
{
    int i;

    *minValue = numbers[0];
    *minIndex = 0;

    for (i = 1; i < size; i++)
        if (numbers[i] < *minValue)
        {
            *minValue = numbers[i];
            *minIndex = i;
        }
}
```

Call it with the addresses: `findMin(numbers, count, &smallest, &position);`. Cast before dividing when the operands are integers, or the average truncates.

### One-dimensional array read from a file

The count is not known in advance, so the read loop drives it and the array capacity guards it.

```c
int main(void)
{
    FILE *inp;                  //pointer to input file
    int numbers[MAX_SIZE],
        count = 0,
        value;

    //Opening the file
    inp = fopen("numbers.txt", "r");

    if (inp == NULL)
    {
        printf("File could not be opened !!\n");
        return(1);
    }

    //Reading into the array
    while (count < MAX_SIZE && fscanf(inp, "%d", &value) == 1)
    {
        numbers[count] = value;
        count++;
    }

    fclose(inp);

    printf("%d numbers were read.\n", count);

    return(0);
}
```

Three non-negotiables: check the pointer against `NULL` after `fopen`, test the return value of `fscanf` rather than `feof`, and `fclose` every file you open.

### Parallel arrays

Related columns are kept in separate arrays sharing one index. Keep them the same length and always update them together.

```c
    char days[MAX_DAYS][DAY_LEN];
    int  dayTemp[MAX_DAYS],
         nightTemp[MAX_DAYS];

    while (count < MAX_DAYS &&
           fscanf(inp, "%s %d %d", days[count], &dayTemp[count], &nightTemp[count]) == 3)
        count++;
```

`fscanf` with `%s` takes the array name without `&`, because the array name is already an address.

### Two-dimensional array

```c
//Computes the average of one column of a matrix
double columnAverage(int matrix[][COLS], int rows, int col)
{
    int row, sum = 0;

    for (row = 0; row < rows; row++)
        sum += matrix[row][col];

    return((double)sum / rows);
}
```

The column size is part of the parameter type and cannot be omitted. Row index first, column index second, everywhere.

### Writing to a file

```c
    FILE *outp;

    outp = fopen("results.txt", "w");

    if (outp == NULL)
    {
        printf("Output file could not be opened !!\n");
        return(1);
    }

    fprintf(outp, "%-15s %8.2f\n", name, average);

    fclose(outp);
```

`"w"` truncates, `"a"` appends, `"r"` reads. `%-15s` left-aligns in a 15-wide field, which is how the expected runs line their columns up.

## Rules with rewrites

**Magic number in the body.**
`payment = payment * 0.75;` becomes `#define DISCOUNT 25` plus `payment *= (100 - DISCOUNT) / 100.0;`.

**Integer division where a fraction is wanted.**
`(100 - DISCOUNT) / 100` evaluates to `0`. It becomes `(100 - DISCOUNT) / 100.0`.

**Average computed with integer arithmetic.**
`return(sum / size);` becomes `return((double)sum / size);`.

**Unvalidated input.**
A bare `scanf` becomes a `scanf` followed by a `while` loop that reprints the prompt until the value is in range.

**Char read straight after a number.**
`scanf("%c", &choice);` becomes `scanf(" %c", &choice);`.

**Missing address operator.**
`scanf("%d", number);` becomes `scanf("%d", &number);`. For a string or an array row, the `&` is not used.

**Unchecked file open.**
`inp = fopen("numbers.txt", "r");` followed straight by a read becomes the same call followed by the `if (inp == NULL)` guard.

**Looping on end of file.**
`while (!feof(inp))` becomes `while (fscanf(inp, "%d", &value) == 1)`, which does not process the last item twice.

**Array written without a bound.**
`while (fscanf(...) == 1) { numbers[count] = value; count++; }` becomes the same loop with `count < MAX_SIZE &&` in front of the read.

**No purpose comment.**
A program starting with `#include` becomes one starting with the `/* ... */` line that names the question and what it does.

**Undescriptive names.**
`double a, b, c;` becomes `double shortSide, longSide, height;`.

**Missing break in a switch.**
A `case` that runs into the next one becomes a `case` ending in `break`, unless the fall-through is intended and commented.

**Output that does not match the expected run.**
Any difference in wording, spacing, decimals, or newlines becomes an exact match with the expected run, checked character by character.

## Failure modes

- Writing `=` where `==` was meant inside an `if`, which assigns and then tests the assigned value.
- A semicolon straight after `if (...)` or `for (...)`, which makes the body an empty statement.
- Reading with `%d` into a `double`, or `%f` into an `int`.
- Off-by-one in an array loop: `for (i = 0; i <= size; i++)` runs one element past the end.
- Comparing strings with `==` instead of `strcmp`.
- Forgetting `#include <math.h>` before using `pow` or `sqrt`.
- Losing the count variable when a file is shorter than expected, so the program prints stale array slots.
- Parallel arrays updated at different indices, which silently misaligns the columns.
- A `while` loop whose control variable is never changed inside the body.
- Returning from `main` without `return(0);`.

## Verification

Before reporting the work as done, confirm all of these:

- The purpose comment, `_CRT_SECURE_NO_WARNINGS`, includes, constants, and `int main(void)` appear in that order.
- Every fixed number in the body is a named constant.
- Every declared variable carries a purpose comment and a descriptive name.
- Every user input is validated with a loop that reprints the prompt.
- Every `fopen` is checked against `NULL` and matched by an `fclose`.
- Every array write is bounded by its capacity.
- Every function has a plain-English contract above it.
- The program output matches the expected run exactly: wording, spacing, decimal places, and line breaks.

## Workflow

1. Restate what the program reads, what it computes, and exactly what it prints.
2. Write the purpose comment and the constant definitions first.
3. Declare the variables in one block with purpose comments.
4. Write the input section with its validation loop.
5. Write the computation, extracting a function whenever a step has a name.
6. Write the display section and match the expected run character by character.
7. Trace one full run by hand with a small input and state the output you expect.
8. Report what was verified and which cases you could not run.
