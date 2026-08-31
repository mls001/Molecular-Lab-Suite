import os
import glob
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from typing import Generator, Dict, Any


def run_mol_optimize_stream(input_folder: str, output_folder: str,
                            prefix: str = "opt_", ff: str = "MMFF94",
                            maxiter: int = 500, embed: bool = True,
                            add_h: bool = True, charge: str = "0",
                            mult: str = "1", keyword: str = "#p opt b3lyp/6-31g(d,p)",
                            mem: str = "20GB", nproc: str = "8") -> Generator[Dict[str, Any], None, None]:
    """
    分子力场优化生成器，每步 yield 坐标和状态
    """
    if not os.path.isdir(input_folder):
        yield {"error": f"输入文件夹不存在: {input_folder}"}
        return

    mol_files = glob.glob(os.path.join(input_folder, "*.mol"))
    if not mol_files:
        yield {"error": "未找到 .mol 文件"}
        return

    os.makedirs(output_folder, exist_ok=True)

    update_interval = 10

    for idx, mol_file in enumerate(mol_files):
        basename = os.path.basename(mol_file)
        name, _ = os.path.splitext(basename)
        output_name = f"{prefix}{name}.gjf"
        output_path = os.path.join(output_folder, output_name)

        yield {
            "type": "molecule_start",
            "filename": basename,
            "index": idx,
            "total": len(mol_files)
        }

        try:
            mol = Chem.MolFromMolFile(mol_file, removeHs=False)
            if mol is None:
                yield {"type": "error", "message": f"无法读取分子: {basename}"}
                continue

            if add_h:
                mol = Chem.AddHs(mol)

            # 检查/生成3D构象
            has_3d = False
            if mol.GetNumConformers() > 0:
                conf = mol.GetConformer()
                positions = conf.GetPositions()
                if not all(abs(pos[2]) < 0.01 for pos in positions):
                    has_3d = True
            if not has_3d and embed:
                AllChem.EmbedMolecule(mol, AllChem.ETKDG())
            elif not has_3d and not embed:
                yield {"type": "warning", "message": f"{basename} 无3D坐标且未启用嵌入"}

            # 决定力场
            ff_use = ff.upper()
            if ff_use == 'MMFF94':
                if not AllChem.MMFFHasAllMoleculeParams(mol):
                    yield {"type": "info", "message": f"MMFF94 不适用 {basename}，回退 UFF"}
                    ff_use = 'UFF'

            # 选择优化函数
            opt_func = AllChem.MMFFOptimizeMolecule if ff_use == 'MMFF94' else AllChem.UFFOptimizeMolecule

            # 发送初始结构
            conf = mol.GetConformer()
            coords = conf.GetPositions().tolist()
            yield {
                "type": "structure",
                "filename": basename,
                "step": 0,
                "coords": coords,
                "status": "initial",
                "converged": False
            }

            # 迭代优化
            for step in range(maxiter):
                try:
                    converged = opt_func(mol, maxIters=1)
                except Exception as e:
                    yield {"type": "error", "message": f"优化步 {step} 出错: {e}"}
                    break

                coords = conf.GetPositions().tolist()

                if step % update_interval == 0:
                    yield {
                        "type": "structure",
                        "filename": basename,
                        "step": step + 1,
                        "coords": coords,
                        "status": "optimizing",
                        "converged": False
                    }

                if converged:
                    yield {
                        "type": "info",
                        "message": f"{basename} 在 {step + 1} 步收敛"
                    }
                    break
            else:
                yield {
                    "type": "info",
                    "message": f"{basename} 达到最大迭代步数 {maxiter}，未完全收敛"
                }

            # 最终坐标
            final_coords = conf.GetPositions().tolist()
            yield {
                "type": "structure",
                "filename": basename,
                "step": maxiter,
                "coords": final_coords,
                "status": "completed",
                "converged": True
            }

            # ---- 生成GJF ----
            atom_lines = []
            for atom, pos in zip(mol.GetAtoms(), final_coords):
                elem = atom.GetSymbol()
                atom_lines.append(f"{elem:<2s}  {pos[0]:12.6f} {pos[1]:12.6f} {pos[2]:12.6f}")
            coord_block = "\n".join(atom_lines)

            chk_name = f"{output_name.replace('.gjf', '.chk')}"
            gjf_content = f"""%chk={chk_name}
%mem={mem}
%nprocshared={nproc}
{keyword}

Optimized from {basename} using {ff_use} force field

{charge} {mult}
{coord_block}

"""
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(gjf_content)

            yield {
                "type": "file_generated",
                "filename": basename,
                "output_path": output_path
            }

        except Exception as e:
            yield {"type": "error", "message": f"处理 {basename} 时出错: {str(e)}"}

    yield {"type": "done", "message": "分子力场优化任务完成。"}
