# 原子序数 → 元素符号
ATOMIC_NUMBER_TO_SYMBOL = {
    1: 'H', 3: 'Li', 4: 'Be', 5: 'B', 6: 'C', 7: 'N', 8: 'O', 9: 'F',
    14: 'Si', 15: 'P', 16: 'S', 17: 'Cl', 34: 'Se', 35: 'Br', 53: 'I'
}

PRESET_RESOURCES = {
    "hachimi单并行": {"nproc": "10", "mem": "40GB"},
    "hachimi四并行": {"nproc": "4", "mem": "10GB"},
    "Tomori八队列": {"nproc": "12", "mem": "12GB"},
    "students": {"nproc": "8", "mem": "20GB"},
    "zstoffice": {"nproc": "8", "mem": "20GB"},
    "zst106": {"nproc": "24", "mem": "180GB"}
}