# 元素周期表（1-118）符号表
_SYMBOLS = (
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni "
    "Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe "
    "Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg "
    "Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg "
    "Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og"
).split()

# 原子序数 → 元素符号（覆盖全部 118 号元素，含 Ir / Pt / Os / Ru 等发光配合物常用金属）
ATOMIC_NUMBER_TO_SYMBOL = {i + 1: sym for i, sym in enumerate(_SYMBOLS)}

# 元素符号 → 原子序数
SYMBOL_TO_ATOMIC_NUMBER = {sym: num for num, sym in ATOMIC_NUMBER_TO_SYMBOL.items()}

PRESET_RESOURCES = {
    "hachimi单并行": {"nproc": "10", "mem": "40GB"},
    "hachimi四并行": {"nproc": "4", "mem": "10GB"},
    "Tomori八队列": {"nproc": "12", "mem": "12GB"},
    "students": {"nproc": "8", "mem": "20GB"},
    "zstoffice": {"nproc": "8", "mem": "20GB"},
    "zst106": {"nproc": "24", "mem": "180GB"}
}
