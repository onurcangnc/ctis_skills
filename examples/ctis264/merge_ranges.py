from __future__ import annotations


def merge_sort(values: list[int]) -> list[int]:
    """Return a sorted copy while preserving duplicate values."""
    if len(values) < 2:
        return values.copy()
    midpoint = len(values) // 2
    left = merge_sort(values[:midpoint])
    right = merge_sort(values[midpoint:])
    merged: list[int] = []
    left_index = 0
    right_index = 0
    while left_index < len(left) and right_index < len(right):
        if left[left_index] <= right[right_index]:
            merged.append(left[left_index])
            left_index += 1
        else:
            merged.append(right[right_index])
            right_index += 1
    merged.extend(left[left_index:])
    merged.extend(right[right_index:])
    return merged


def self_check() -> None:
    assert merge_sort([4, -1, 4, 0]) == [-1, 0, 4, 4]
    assert merge_sort([]) == []
    original = [2, 1]
    assert merge_sort(original) == [1, 2]
    assert original == [2, 1]


if __name__ == "__main__":
    self_check()
    print("MERGE_OK")
