<template>
  <div class="flex-col h-full" style="gap:6px;overflow:hidden;">
    <div class="flex flex-1 min-h-0" style="gap:6px;">

      <!-- ===== 左：分子文件 / PubChem 检索 ===== -->
      <aside class="flex-col mls-panel" style="width:240px;flex-shrink:0;min-height:0;">
        <div class="mls-panel-head">
          <span>{{ $t('分子文件') }}</span>
          <button class="btn" style="height:20px;padding:0 8px;font-size:11px;" @click="refreshList">{{ $t('刷新') }}</button>
        </div>
        <div class="mls-subhead" :title="folder">{{ folder || $t('未选择目录') }}</div>
        <div class="flex" style="gap:4px;padding:4px 6px;border-bottom:1px solid var(--c-border-soft);">
          <button class="btn" style="flex:1;height:22px;font-size:11px;" @click="chooseFolder">{{ $t('选择文件夹…') }}</button>
          <button class="btn" style="flex:1;height:22px;font-size:11px;" @click="useMolsDir">{{ $t('Mols 目录') }}</button>
        </div>
        <div class="flex" style="gap:4px;padding:4px 6px;border-bottom:1px solid var(--c-border-soft);">
          <button class="btn" style="flex:1;height:22px;font-size:11px;" @click="newMolecule">{{ $t('新建分子') }}</button>
        </div>

        <!-- PubChem 检索（对标 MolView 搜索框） -->
        <div class="mls-subhead">{{ $t('PubChem 检索') }}</div>
        <div class="flex-col" style="gap:4px;padding:4px 6px;border-bottom:1px solid var(--c-border-soft);">
          <div class="flex-center" style="gap:4px;">
            <input class="control" style="flex:1;min-width:0;height:22px;font-size:11px;" v-model="fetchQuery"
                   :placeholder="$t('名称 / CID / SMILES')" @keydown.enter="fetchPubChem" />
            <button class="btn btn-primary" style="height:22px;font-size:11px;" @click="fetchPubChem" :disabled="busy">{{ $t('检索') }}</button>
          </div>
          <select class="control" style="width:100%;height:22px;font-size:11px;" v-model="fetchKind">
            <option value="name">{{ $t('按名称') }}</option>
            <option value="cid">{{ $t('按 CID') }}</option>
            <option value="smiles">{{ $t('按 SMILES') }}</option>
          </select>
        </div>

        <div style="flex:1;overflow-y:auto;padding:2px 0;min-height:0;">
          <div v-if="!files.length" class="ide-empty">{{ $t('目录里没有分子文件') }}</div>
          <div
            v-for="f in files"
            :key="f.path"
            class="flex-center"
            style="gap:6px;padding:3px 8px;cursor:pointer;font-size:12px;"
            :style="{ background: activeName === f.name ? 'var(--c-hl-a)' : 'transparent' }"
            @click="openFile(f)"
            @mouseenter="ev => { if (activeName !== f.name) ev.currentTarget.style.background = 'var(--c-hover)' }"
            @mouseleave="ev => { if (activeName !== f.name) ev.currentTarget.style.background = 'transparent' }"
          >
            <span style="flex-shrink:0;font-size:10px;font-weight:700;color:var(--c-text-3);">{{ f.ext.replace('.', '').toUpperCase() }}</span>
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" :style="{ fontWeight: f.is_mls ? 700 : 400 }">{{ f.name }}</span>
          </div>
        </div>
      </aside>

      <!-- ===== 中：2D 绘制 + 3D 模型（MolView 布局） ===== -->
      <section class="flex-col mls-panel" style="flex:1;min-width:0;min-height:0;">
        <div class="mls-toolbar" style="justify-content:space-between;">
          <div class="flex-center" style="gap:8px;min-width:0;flex:1;">
            <span style="font-weight:700;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
              {{ mol.name || $t('未命名分子') }}
            </span>
            <span v-if="mol.n_atoms" style="font-size:11px;color:var(--c-text-3);">
              {{ mol.formula }} · {{ mol.n_atoms }} {{ $t('原子') }} · {{ mol.n_bonds }} {{ $t('键') }}
            </span>
          </div>
          <span v-if="syncing3d" style="font-size:11px;color:var(--c-text-2);flex-shrink:0;">{{ $t('3D 同步中…') }}</span>
        </div>

        <div class="flex flex-1 min-h-0" style="gap:0;">
          <!-- 2D 结构式（左）：顶部工具条 + 左侧工具 + 画布 + 右侧元素栏 -->
          <div class="flex-col" style="flex:1;min-width:0;min-height:0;">
            <!-- 顶部绘制工具栏（图标，对标 MolView） -->
            <div class="mv-topbar">
              <button class="mv-ibtn" :disabled="!undoStack.length" :title="$t('撤销')" @click="undo"><MolIcon name="undo" /></button>
              <button class="mv-ibtn" :disabled="!redoStack.length" :title="$t('重做')" @click="redo"><MolIcon name="redo" /></button>
              <button class="mv-ibtn" :disabled="busy || !mol.n_atoms" :title="$t('整理结构')" @click="cleanUp"><MolIcon name="clean" /></button>
              <button class="mv-ibtn" :disabled="selected === null && bondSel < 0" :title="$t('删除')" @click="deleteSelection"><MolIcon name="trash" /></button>
              <span class="mv-sep-v"></span>
              <button class="mv-ibtn" :title="$t('放大')" @click="zoomCanvas(1.25)"><MolIcon name="zoomIn" /></button>
              <button class="mv-ibtn" :title="$t('缩小')" @click="zoomCanvas(0.8)"><MolIcon name="zoomOut" /></button>
              <button class="mv-ibtn" :title="$t('适应窗口')" @click="refit"><MolIcon name="fit" /></button>
              <span class="mv-sep-v"></span>
              <button class="mv-ibtn" :class="{ 'mv-ibtn-on': showExplicitCH }"
                      :title="$t('显示碳/氢标签（非骨架式）')" @click="showExplicitCH = !showExplicitCH">
                <span style="font-size:11px;font-weight:700;">CH</span>
              </button>
              <span style="flex:1;"></span>
              <button class="mv-ibtn" :title="$t('导出结构式图片 (SVG)')" @click="export2d('svg')" :disabled="!mol.n_atoms"><MolIcon name="download" /></button>
            </div>

            <!-- 结构不合法提示（画到一半的 5 价碳等） -->
            <div v-if="validError" class="mv-warn">
              <span style="font-weight:700;">{{ $t('结构不合法') }}</span>
              <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" :title="validError">{{ validError }}</span>
              <span style="flex-shrink:0;color:var(--c-text-2);">{{ $t('请修正后再保存/生成输入文件') }}</span>
            </div>

            <div class="flex flex-1 min-h-0" style="gap:0;">
              <!-- 左侧绘制工具栏（工具） -->
              <div class="mv-toolstrip">
                <button
                  v-for="t in tools" :key="t.id"
                  class="mv-tool" :class="{ 'mv-tool-on': toolActive(t) }"
                  :title="$t(t.tip)" @click="activateTool(t, $event)"
                ><MolIcon :name="t.icon" /><span v-if="t.menu" class="mv-sub">▸</span></button>
              </div>

              <MolCanvas2D
                ref="canvas"
                :atoms="mol.atoms"
                :bonds="mol.bonds"
                :selected="selected"
                :selected-bond="bondSel"
                :show-indices="showIndices"
                :show-explicit-c-h="showExplicitCH"
                :element="elementChoice"
                :bond-order="bondOrder"
                :charge-delta="chargeDelta"
                :tool="tool"
                :select-mode="selectMode"
                :arm-ring="armRing"
                :background="bgTheme"
                :selected-atoms="selectedAtoms"
                :warn-atom="warnAtom"
                :hint="canvasHint"
                @select-atom="onSelectAtom"
                @select-atoms="onSelectAtoms"
                @select-bond="onSelectBond"
                @add-atom="onAddAtom"
                @add-atom-chain="onAddAtomChain"
                @add-bond="onAddBond"
                @add-bond-atom="onAddBondAtom"
                @cycle-bond="onCycleBond"
                @charge-atom="onChargeAtom"
                @extend-atom="onExtendAtom"
                @hover-atom="hoverAtom = $event"
                @move-atom="onMoveAtom"
                @delete-atom="onDeleteAtom"
                @delete-bond="onDeleteBond"
                @place-ring="onPlaceRing"
              />

              <!-- 右侧元素栏 -->
              <div class="mv-palette">
                <button
                  v-for="el in paletteElements" :key="el"
                  class="mv-el" :class="{ 'mv-el-on': elementChoice === el }"
                  :title="$t('点元素改选中原子；也可把鼠标悬停在原子上按字母键（大写=小序数，小写=大序数）')"
                  @click="pickElement(el)"
                >{{ el }}</button>
                <button class="mv-el" style="font-weight:700;" @click.stop="toggleMenu('palette', $event)" title="…">…</button>
              </div>
            </div>
          </div>

          <!-- 3D 模型（右）：默认启用，随绘制自动更新 -->
          <div class="flex-col" style="flex:1;min-width:0;min-height:0;">
            <div class="mls-toolbar" style="gap:0;position:relative;">
              <div class="flex-center" style="gap:0;">
                <div v-for="m in menus" :key="m.id" class="mv-menu">
                  <button class="btn btn-default mv-menu-btn" :class="{ 'mv-menu-open': openMenu === m.id }"
                          style="height:22px;font-size:11px;padding:0 10px;" @click.stop="toggleMenu(m.id, $event)">{{ $t(m.label) }} ▾</button>
                </div>
              </div>
              <div style="flex:1;"></div>
              <span v-if="syncing3d" style="font-size:11px;color:var(--c-text-2);padding-right:8px;">{{ $t('3D 同步中…') }}</span>
            </div>

            <EmptyNotice
              v-if="!mol3d || !mol3d.molblock"
              :text="$t('还没有 3D 模型')"
            />
            <MolViewer
              v-else
              ref="viewer"
              :molblock="mol3d.molblock"
              :selected="selected"
              :selected-bond-atoms="selBondAtoms"
              :show-indices="showIndices"
              :representation="representation"
              :background="bgTheme"
              :charges="charges"
              :overlay="measureOverlay"
              @select="onViewerSelect"
              @background-click="clearSelection"
            />

            <div class="mls-subhead" :title="measureText || ''">
              <span v-if="measureText">{{ measureText }}</span>
              <span v-else-if="measureMode">{{ $t('测量中：在 3D 模型上依次点击原子') }}（{{ measurePicks.length }}/{{ measureNeed }}）</span>
              <span v-else-if="syncing3d">{{ $t('3D 同步中…') }}</span>
            </div>
          </div>
        </div>

        <div class="mls-subhead" :title="noteText">
          <span v-if="selectedAtoms.length > 1">{{ $t('已选中 {0} 个原子', { 0: selectedAtoms.length }) }}</span>
          <span v-else-if="selected !== null && selected >= 0">{{ $t('已选中原子') }} {{ selected }} ({{ selectedSymbol }})</span>
          <span v-else-if="bondSel >= 0 && mol.bonds[bondSel]">{{ $t('已选中键') }} {{ mol.bonds[bondSel].a }}-{{ mol.bonds[bondSel].b }}</span>
          <span v-if="noteText" :style="{ color: validError ? 'var(--c-warning)' : 'var(--c-text-3)' }">{{ noteText }}</span>
        </div>
      </section>

      <!-- ===== 右：化学数据 / 编辑 / 保存 ===== -->
      <aside class="flex-col mls-panel" style="width:290px;flex-shrink:0;overflow-y:auto;padding:8px 10px;gap:8px;min-height:0;">

        <div class="flex-col" style="gap:4px;">
          <span class="label">{{ $t('分子信息') }}</span>
          <div class="flex-center" style="justify-content:space-between;font-size:11px;color:var(--c-text-2);">
            <span>{{ $t('分子式') }}</span><span>{{ mol.formula || '—' }}</span>
          </div>
          <div class="flex-center" style="justify-content:space-between;font-size:11px;color:var(--c-text-2);">
            <span>{{ $t('分子量') }}</span><span>{{ mol.mw || '—' }}</span>
          </div>
          <div class="flex-center" style="justify-content:space-between;font-size:11px;color:var(--c-text-2);">
            <span>{{ $t('总电荷') }}</span><span>{{ mol.charge || 0 }}</span>
          </div>
          <div class="flex-center" style="gap:8px;font-size:11px;color:var(--c-text-2);">
            <span class="flex-center" style="gap:4px;flex:1;">
              {{ $t('自旋') }}<input class="control" style="width:52px;height:22px;" v-model.number="mol.mult" type="number" min="1" @change="syncStore" />
            </span>
          </div>
        </div>

        <!-- 化学数据（对标 MolView Tools → Chemical data） -->
        <div class="flex-col" style="gap:4px;border-top:1px solid var(--c-border-soft);padding-top:8px;">
          <div class="flex-center" style="justify-content:space-between;">
            <span class="label">{{ $t('化学数据') }}</span>
            <span class="flex-center" style="gap:4px;">
              <button class="btn" style="height:20px;padding:0 6px;font-size:11px;" @click="openExternal('pubchem')" :title="$t('物质信息（PubChem）')">PubChem</button>
              <button class="btn" style="height:20px;padding:0 6px;font-size:11px;" @click="openExternal('nist')" :title="$t('谱图（NIST WebBook）')">NIST</button>
              <button class="btn" style="height:20px;padding:0 6px;font-size:11px;" @click="loadDescriptors" :disabled="busy || !mol.n_atoms">{{ $t('刷新') }}</button>
            </span>
          </div>
          <div v-if="!desc" class="ide-empty" style="padding:6px 0;">{{ $t('点「刷新」获取化学数据') }}</div>
          <template v-else>
            <div v-for="row in descriptorRows" :key="row[0]" class="flex-center"
                 style="justify-content:space-between;font-size:11px;color:var(--c-text-2);gap:6px;">
              <span style="flex-shrink:0;">{{ $t(row[0]) }}</span>
              <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" :title="String(row[1])">{{ row[1] }}</span>
            </div>
            <div v-if="dipole" class="flex-center" style="justify-content:space-between;font-size:11px;color:var(--c-text-2);">
              <span>{{ $t('整体偶极') }}</span><span>{{ Number(dipole.magnitude).toFixed(2) }} D</span>
            </div>
          </template>
        </div>

        <!-- 保存 -->
        <div class="flex-col" style="gap:5px;border-top:1px solid var(--c-border-soft);padding-top:8px;">
          <span class="label">{{ $t('保存为 .mls') }}</span>
          <div class="flex-center" style="gap:6px;">
            <input class="control" style="flex:1;min-width:0;height:24px;" v-model="saveName" :placeholder="$t('输入分子名称')" @keydown.enter="saveMls" />
            <button class="btn btn-primary" style="height:24px;font-size:11px;" @click="saveMls" :disabled="busy || !mol.n_atoms">{{ saving ? $t('保存中…') : $t('保存') }}</button>
          </div>
          <label class="flex-center" style="gap:5px;font-size:11px;color:var(--c-text-2);cursor:pointer;">
            <input type="checkbox" v-model="saveWithH" /> {{ $t('保存前加显式氢（做计算用）') }}
          </label>
          <label v-if="has3d" class="flex-center" style="gap:5px;font-size:11px;color:var(--c-text-2);cursor:pointer;">
            <input type="checkbox" v-model="saveFrom3d" /> {{ $t('用 3D 模型坐标保存') }}
          </label>
          <div style="font-size:11px;color:var(--c-text-3);word-break:break-all;">{{ molsDir }}</div>
          <div class="flex" style="gap:6px;">
            <button class="btn" style="flex:1;height:24px;font-size:11px;" @click="saveMlsAs" :disabled="busy || !mol.n_atoms">{{ $t('另存到…') }}</button>
            <button class="btn" style="flex:1;height:24px;font-size:11px;" @click="gotoInputGen" :disabled="!mol.n_atoms">{{ $t('生成输入文件') }}</button>
          </div>
          <div class="flex" style="gap:6px;">
            <button class="btn" style="flex:1;height:24px;font-size:11px;" @click="addHs" :disabled="busy || !mol.n_atoms">{{ $t('加显式氢') }}</button>
            <button class="btn" style="flex:1;height:24px;font-size:11px;" @click="removeHs" :disabled="busy || !mol.n_atoms">{{ $t('去显式氢') }}</button>
          </div>
        </div>
      </aside>
    </div>

    <LogViewer :lines="logLines" />

    <!-- 菜单下拉（fixed 定位，避免被面板 overflow 裁掉） -->
    <MolMenuPanel v-if="openMenu && activeMenuItems.length" :left="menuPos.left" :top="menuPos.top" :min-width="230">
      <template v-for="(it, i) in activeMenuItems" :key="i">
        <div v-if="it.sep" class="mv-menu-sep"></div>
        <button v-else class="mv-menu-item" @click="runMenuItem(it)">
          <span style="width:12px;display:inline-block;">{{ isChecked(it) ? '✓' : '' }}</span>
          <span>{{ $t(it.label) }}</span>
        </button>
      </template>
    </MolMenuPanel>

    <!-- 元素栏「…」：更多元素 -->
    <MolMenuPanel v-if="openMenu === 'palette'" :left="menuPos.left" :top="menuPos.top" :min-width="220">
      <div class="mv-panel-title">{{ $t('更多元素') }}</div>
      <div class="flex" style="flex-wrap:wrap;gap:3px;padding:2px 8px 8px 8px;">
        <button v-for="el in moreElements" :key="el" class="btn"
                :class="elementChoice === el ? 'btn-primary' : 'btn-default'"
                style="width:32px;height:22px;font-size:11px;padding:0;" @click="pickElement(el)">
          {{ el }}
        </button>
      </div>
    </MolMenuPanel>

    <!-- 左侧工具的二级菜单：环模板 / 电荷 -->
    <MolMenuPanel v-if="toolMenu" :left="menuPos.left" :top="menuPos.top" :min-width="190">
      <template v-if="toolMenu === 'select'">
        <div class="mv-panel-title">{{ $t('框选方式') }}</div>
        <button class="mv-menu-item" @click="setSelectMode('rect')">
          <span style="width:12px;display:inline-block;">{{ selectMode === 'rect' ? '✓' : '' }}</span>
          <span>{{ $t('矩形框选') }}</span>
        </button>
        <button class="mv-menu-item" @click="setSelectMode('lasso')">
          <span style="width:12px;display:inline-block;">{{ selectMode === 'lasso' ? '✓' : '' }}</span>
          <span>{{ $t('曲线框选（套索）') }}</span>
        </button>
      </template>
      <template v-else-if="toolMenu === 'charge'">
        <div class="mv-panel-title">{{ $t('电荷') }}</div>
        <button class="mv-menu-item" @click="setChargeDelta(1)">
          <span style="width:12px;display:inline-block;">{{ chargeDelta > 0 ? '✓' : '' }}</span>
          <span>{{ $t('加正电荷（e+）') }}</span>
        </button>
        <button class="mv-menu-item" @click="setChargeDelta(-1)">
          <span style="width:12px;display:inline-block;">{{ chargeDelta < 0 ? '✓' : '' }}</span>
          <span>{{ $t('加负电荷（e−）') }}</span>
        </button>
      </template>
              <template v-else>
                <div class="mv-panel-title">{{ $t('环模板') }}</div>
                <div class="flex" style="flex-wrap:wrap;gap:3px;padding:2px 8px 8px 8px;">
                  <button v-for="r in rings" :key="r.id" class="mv-thumb"
                          :class="{ 'mv-thumb-on': armRing && armRing.id === r.id }"
                          :title="$t(r.label)" @click="pickRing(r)"
                          v-html="ringThumbs[r.id]"></button>
                </div>
              </template>
    </MolMenuPanel>
  </div>
</template>

<script>
import LogViewer from '@/components/LogViewer.vue'
import EmptyNotice from '@/components/EmptyNotice.vue'
import MolViewer from '@/components/MolViewer.vue'
import MolCanvas2D from '@/components/MolCanvas2D.vue'
import MolIcon from '@/components/MolIcon.vue'
import MolMenuPanel from '@/components/MolMenuPanel.vue'
import { pickDirectory } from '@/api/dialog'
import { useMoleculeStore } from '@/stores/molecule'
import { currentTheme, applyTheme } from '@/theme/theme'
import { elementForKey, freeBondPosition, thumbnailSvg } from '@/utils/molDraw'
import { tNote } from '@/i18n/notes'
import { t as $tr } from '@/i18n'

const ELEMENTS = ['H', 'C', 'N', 'O', 'F', 'P', 'S', 'Cl', 'Br', 'I', 'B', 'Si',
                  'Se', 'Na', 'K', 'Mg', 'Ca', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
                  'Ru', 'Rh', 'Pd', 'Ag', 'Ir', 'Pt', 'Au', 'Hg']

const EMPTY_MOL = {
  molblock: '', atoms: [], bonds: [], formula: '', mw: 0, smiles: '',
  n_atoms: 0, n_bonds: 0, name: '', noteRaw: '', charge: 0, mult: 1, is3d: false
}

const MEASURE_NEED = { distance: 2, angle: 3, torsion: 4 }

function sub(a, b) { return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z } }
function dot(a, b) { return a.x * b.x + a.y * b.y + a.z * b.z }
function len(a) { return Math.sqrt(dot(a, a)) }
function cross(a, b) {
  return { x: a.y * b.z - a.z * b.y, y: a.z * b.x - a.x * b.z, z: a.x * b.y - a.y * b.x }
}
function angleDeg(a, b, c) {
  const u = sub(a, b), v = sub(c, b)
  const lu = len(u), lv = len(v)
  if (lu < 1e-9 || lv < 1e-9) return 0
  let cosv = dot(u, v) / (lu * lv)
  cosv = Math.max(-1, Math.min(1, cosv))
  return Math.acos(cosv) * 180 / Math.PI
}
function torsionDeg(a, b, c, d) {
  const b1 = sub(b, a), b2 = sub(c, b), b3 = sub(d, c)
  const n1 = cross(b1, b2), n2 = cross(b2, b3)
  const m = cross(n1, { x: b2.x / (len(b2) || 1), y: b2.y / (len(b2) || 1), z: b2.z / (len(b2) || 1) })
  let x = dot(n1, n2), y = dot(m, n2)
  if (Math.abs(x) < 1e-9 && Math.abs(y) < 1e-9) return 0
  return Math.atan2(y, x) * 180 / Math.PI
}

export default {
  name: 'MoleculeView',
  components: { LogViewer, EmptyNotice, MolViewer, MolCanvas2D, MolIcon, MolMenuPanel },
  data() {
    return {
      backendUrl: '',
      molsDir: '',
      folder: '',
      files: [],
      activeName: '',
      // 2D 画布上的结构（编辑的唯一入口）
      mol: { ...EMPTY_MOL },
      // 3D 模型（查看/测量/导出用），与画布坐标分开保存
      mol3d: null,
      stale3d: false,
      syncing3d: false,
      theme: currentTheme(),
      representation: 'ballstick',
      charges: [],
      dipole: null,
      desc: null,
      openMenu: '',
      toolMenu: '',
      menuPos: { left: 40, top: 60 },
      measureMode: null,              // distance | angle | torsion
      measurePicks: [],
      measurements: [],
      tool: 'bond',                   // 画布工具：select | bond | ring | charge | erase
      tools: [
        { id: 'select', label: '选择', icon: 'select', tip: '选择：点原子选中，拖动移动原子；空白处拖出矩形/曲线框选', menu: 'select' },
        { id: 'bond1', base: 'bond', order: 1, label: '单键', icon: 'bond1', tip: '单键：拖动画键；单击原子自动接一个键；单击已有键切换键级' },
        { id: 'bond2', base: 'bond', order: 2, label: '双键', icon: 'bond2', tip: '双键：拖动画出双键；单击已有键切换键级' },
        { id: 'bond3', base: 'bond', order: 3, label: '三键', icon: 'bond3', tip: '三键：拖动画出三键；单击已有键切换键级' },
        { id: 'ring6', base: 'ring', ring: 'benzene', label: '苯环', icon: 'ring6', tip: '苯环：点画布放置，点原子稠合' },
        { id: 'ring5', base: 'ring', ring: 'cyclopentane', label: '环戊烷', icon: 'ring5', tip: '环戊烷：点画布放置，点原子稠合' },
        { id: 'ring3', base: 'ring', ring: 'cyclopropane', label: '环丙烷', icon: 'ring3', tip: '环丙烷：点画布放置，点原子稠合' },
        { id: 'ringmore', base: 'ring', label: '更多环', icon: 'chain', tip: '更多环模板（含杂环 / 稠环）', menu: 'ring' },
        { id: 'charge', label: '电荷', icon: 'chargePlus', tip: '电荷：点原子加正/负电荷（在二级菜单里切换）', menu: 'charge' },
        { id: 'erase', label: '橡皮', icon: 'erase', tip: '橡皮：点原子或键删除' }
      ],
      chargeDelta: 1,
      hoverAtom: null,                // 鼠标悬停的原子（字母键改元素用）
      validError: '',                 // 结构不合法时的原因（空字符串 = 合法）
      showExplicitCH: false,
      bondOrder: 1,
      armRing: null,                  // 环工具当前模板
      showCharges: false,
      _liveTimer: null,
      rings: [],
      selected: null,
      bondSel: -1,
      selectedAtoms: [],              // 框选/曲线选中的多个原子
      selectMode: 'rect',             // rect | lasso
      elementChoice: 'C',
      fetchQuery: '',
      fetchKind: 'name',
      saveName: '',
      saveWithH: true,
      saveFrom3d: true,
      saving: false,
      busy: false,
      laid2d: false,
      elements: ELEMENTS,
      undoStack: [],
      redoStack: [],
      logLines: [],
      menus: [
        {
          id: 'export', label: '导出',
          items: [
            { label: '结构式图片 (SVG)', action: () => this.export2d('svg') },
            { label: '结构式图片 (PNG)', action: () => this.export2d('png') },
            { label: '3D 模型图片 (PNG)', action: () => this.export3dPng() },
            { sep: true },
            { label: 'MOL 文件', action: () => this.exportMol() },
            { label: 'MOL 文件（3D 坐标）', action: () => this.exportMol(true) },
            { label: '.mls 坐标文件', action: () => this.saveMls() }
          ]
        },
        {
          id: 'model', label: '模型',
          items: [
            { label: '重置视图', action: () => this.refit() },
            { sep: true },
            { label: '球棍模型', radio: 'repr', value: 'ballstick', action: () => { this.representation = 'ballstick' } },
            { label: '棒状模型', radio: 'repr', value: 'stick', action: () => { this.representation = 'stick' } },
            { label: '空间填充模型', radio: 'repr', value: 'spacefill', action: () => { this.representation = 'spacefill' } },
            { label: '线框模型', radio: 'repr', value: 'wireframe', action: () => { this.representation = 'wireframe' } },
            { label: '线型模型', radio: 'repr', value: 'line', action: () => { this.representation = 'line' } },
            { sep: true },
            { label: '显示原子序号', toggle: 'showIndices', action: () => { this.showIndices = !this.showIndices } },
            { label: '原子电荷着色（Gasteiger）', toggle: 'showCharges', action: () => this.toggleCharges() },
            { sep: true },
            { label: '重新生成 3D（能量最小化）', action: () => this.optimize3d() }
          ]
        },
        {
          id: 'measure', label: '测量',
          items: [
            { label: '距离', radio: 'measure', value: 'distance', action: () => this.setMeasure('distance') },
            { label: '键角', radio: 'measure', value: 'angle', action: () => this.setMeasure('angle') },
            { label: '扭转角', radio: 'measure', value: 'torsion', action: () => this.setMeasure('torsion') },
            { sep: true },
            { label: '清除测量', action: () => this.clearMeasure() }
          ]
        }
      ]
    }
  },
  computed: {
    has3d() { return !!(this.mol3d && this.mol3d.molblock) },
    // 不合法的原子序号（RDKit 消息形如 "Explicit valence for atom # 3 C, 5, ..."）→ 画布上标红
    warnAtom() {
      if (!this.validError) return null
      const m = /atom #\s*(\d+)/.exec(this.validError)
      return m ? Number(m[1]) : null
    },
    selBondAtoms() {
      const b = (this.mol.bonds || [])[this.bondSel]
      return b ? [b.a, b.b] : null
    },
    // 环模板缩略图（用同一套渲染函数，不另写画法）
    ringThumbs() {
      const out = {}
      for (const r of this.rings) {
        if (r.atoms && r.atoms.length) out[r.id] = thumbnailSvg(r.atoms, r.bonds, 26, 5)
      }
      return out
    },
    // 后端操作说明按当前语言实时翻译（存的是原始中文，切换语言时跟着变）
    noteText() { return tNote(this.mol.noteRaw) },
    activeMenuItems() {
      const m = this.menus.find(x => x.id === this.openMenu)
      return m ? m.items : []
    },
    // 调色板常显元素（MolView 的 C H N O P S F Cl Br I …）
    paletteElements() { return ['H', 'C', 'N', 'O', 'P', 'S', 'F', 'Cl', 'Br', 'I'] },
    moreElements() { return ELEMENTS.filter(e => !this.paletteElements.includes(e)) },
    selectedSymbol() {
      const a = (this.mol.atoms || []).find(x => x.index === this.selected)
      return a ? a.symbol : ''
    },
    canvasHint() {
      if (this.tool === 'select') return $tr('选择：点原子选中，拖动移动原子；点空白拖动平移画布')
      if (this.tool === 'erase') return $tr('橡皮：点原子或键即可删除')
      if (this.tool === 'ring') {
        const r = this.armRing
        return $tr('环：点画布放置{0}，点原子稠合', { 0: r ? $tr(r.label) : $tr('环模板') })
      }
      if (this.tool === 'charge') return $tr('电荷：点原子加{0}', { 0: this.chargeDelta > 0 ? $tr('正电荷') : $tr('负电荷') })
      return $tr('键：单击原子自动接键 · 拖动画键 · 单击键切换键级 · 单击空白放原子 · Delete 删除')
    },
    bgTheme() {
      // 3D 背景跟随明暗主题（默认灰色）
      return this.theme === 'dark' ? '#33383d' : '#c9ced5'
    },
    measureNeed() { return MEASURE_NEED[this.measureMode] || 0 },
    descriptorRows() {
      const d = this.desc
      if (!d) return []
      const rows = [
        ['分子式', d.formula || '—'],
        ['分子量', d.mw],
        ['精确质量', d.exact_mass],
        ['元素组成', (d.elements || []).map(e => e.symbol + e.count).join(' ') || '—'],
        ['重原子', d.n_heavy],
        ['键数', d.n_bonds],
        ['可旋转键', d.rotatable],
        ['氢键给体', d.hbd],
        ['氢键受体', d.hba],
        ['极性表面积', d.tpsa],
        ['环数', d.rings],
        ['芳香环', d.aromatic_rings],
        ['LogP', d.logp],
        ['总电荷', d.charge],
        ['SMILES', d.smiles || '—'],
        ['InChI', d.inchi || '—'],
        ['InChIKey', d.inchikey || '—']
      ]
      return rows
    },
    measureText() {
      if (!this.measurements.length) return ''
      return this.measurements.map(m => `${this.$t(this.measureLabel(m.type))} ${m.text}`).join('　·　')
    },
    // 3D 叠加层：测量用虚线 + 数值标签 + 偶极箭头
    measureOverlay() {
      const lines = []
      const labels = []
      const arrows = []
      const at = (i) => {
        const src = (this.mol3d && (this.mol3d.atoms || []).length) ? this.mol3d.atoms : this.mol.atoms
        return (src || []).find(a => a.index === i)
      }
      for (const m of this.measurements) {
        const P = m.atoms.map(at).filter(Boolean)
        for (let i = 0; i + 1 < P.length; i++) {
          lines.push({ x1: P[i].x, y1: P[i].y, z1: P[i].z, x2: P[i + 1].x, y2: P[i + 1].y, z2: P[i + 1].z })
        }
        if (!P.length) continue
        // 标签放在测量中心稍微偏移处
        const cx = P.reduce((s, p) => s + p.x, 0) / P.length
        const cy = P.reduce((s, p) => s + p.y, 0) / P.length
        const cz = P.reduce((s, p) => s + p.z, 0) / P.length
        labels.push({ x: cx, y: cy, z: cz + 0.35, text: `${this.$t(this.measureLabel(m.type))} ${m.text}` })
      }
      // 正在测量时高亮已选原子
      for (const i of this.measurePicks) {
        const p = at(i)
        if (p) labels.push({ x: p.x, y: p.y, z: p.z + 0.3, text: `${i}` })
      }
      // 偶极箭头（从质心出发）
      if (this.dipole && this.mol3d && (this.mol3d.atoms || []).length) {
        const as = this.mol3d.atoms
        const cx = as.reduce((s, a) => s + a.x, 0) / as.length
        const cy = as.reduce((s, a) => s + a.y, 0) / as.length
        const cz = as.reduce((s, a) => s + a.z, 0) / as.length
        const mag = Math.max(1e-6, Math.hypot(this.dipole.x, this.dipole.y, this.dipole.z))
        const k = Math.min(3.0, 0.8 + mag * 0.35) / mag
        arrows.push({
          x1: cx, y1: cy, z1: cz,
          x2: cx + this.dipole.x * k, y2: cy + this.dipole.y * k, z2: cz + this.dipole.z * k
        })
      }
      // 选中高亮（3D 里只画线框外框，保留原子本身的元素颜色）
      const highlights = []
      const fillR = this.representation === 'spacefill' ? 2.0 : (this.representation === 'ballstick' ? 0.6 : 0.42)
      const picked = (this.selectedAtoms && this.selectedAtoms.length) ? this.selectedAtoms : (this.selected !== null ? [this.selected] : [])
      for (const idx of picked) {
        const p = at(idx)
        if (p) highlights.push({ kind: 'sphere', x: p.x, y: p.y, z: p.z, radius: fillR, color: '#ffb300' })
      }
      const sb = this.selBondAtoms
      if (sb) {
        const p1 = at(sb[0]); const p2 = at(sb[1])
        if (p1 && p2) {
          highlights.push({ kind: 'cylinder', x: p1.x, y: p1.y, z: p1.z, x2: p2.x, y2: p2.y, z2: p2.z,
                            radius: 0.24, color: '#ff7a00' })
        }
      }
      return { lines, labels, arrows, highlights }
    }
  },
  async mounted() {
    this.backendUrl = await this.getBackendUrl()
    try {
      const r = await fetch(`${this.backendUrl}/api/mol/presets`)
      const d = await r.json()
      this.molsDir = d.mols_dir || ''
      this.rings = d.rings || []
    } catch (e) {
      this.addLog($tr('读取后端设置失败: {0}', { 0: e.message }), '#ff6b6b')
    }
    if (!this.molsDir) {
      // 兜底：直接问后端 Mols 目录，保证分子页默认就在 Mols 路径
      try {
        const r2 = await fetch(`${this.backendUrl}/api/mol/mols`)
        const d2 = await r2.json()
        this.molsDir = d2.dir || ''
      } catch (e) { /* ignore */ }
    }
    this.folder = this.molsDir
    window.addEventListener('keydown', this.onKey)
    window.addEventListener('click', this.closeMenus)
    window.addEventListener('mls-theme-change', this.onThemeChange)
    await this.refreshList()
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKey)
    window.removeEventListener('click', this.closeMenus)
    window.removeEventListener('mls-theme-change', this.onThemeChange)
    if (this._liveTimer) clearTimeout(this._liveTimer)
  },
  methods: {
    addLog(text, color = '#d4d4d4') {
      this.logLines.push({ text, color })
      if (this.logLines.length > 200) this.logLines.shift()
    },
    async getBackendUrl() {
      if (window.electronAPI && typeof window.electronAPI.getBackendUrl === 'function') {
        try { return await window.electronAPI.getBackendUrl() } catch (e) { /* fallthrough */ }
      }
      return 'http://127.0.0.1:8002'
    },
    async postJson(url, body) {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
      })
      const text = await resp.text()
      let data = {}
      if (text) {
        try { data = JSON.parse(text) } catch (e) {
          data = { detail: text.length > 400 ? text.slice(0, 400) + '…' : text }
        }
      }
      return { ok: resp.ok, status: resp.status, data }
    },

    // ===== 菜单 =====
    toggleMenu(id, ev) {
      if (this.openMenu === id) { this.openMenu = ''; return }
      const r = ev && ev.currentTarget ? ev.currentTarget.getBoundingClientRect() : { left: 40, bottom: 60 }
      const w = 230
      this.menuPos = {
        left: Math.max(4, Math.min(Math.round(r.left), window.innerWidth - w - 8)),
        top: Math.round(r.bottom)
      }
      this.openMenu = id
      this.toolMenu = ''
    },
    closeMenus(ev) {
      this.openMenu = ''
      // 刚点开二级菜单的那一下点击会冒泡到 window，这里要放过（否则菜单一闪就没）
      if (this._menuAt && Date.now() - this._menuAt < 300) return
      const t = ev && ev.target
      if (t && t.closest && t.closest('.mv-tool')) return
      this.toolMenu = ''
    },
    onThemeChange(e) {
      this.theme = (e && e.detail) || currentTheme()
    },
    runMenuItem(it) {
      this.openMenu = ''
      if (typeof it.action === 'function') it.action()
    },
    isChecked(it) {
      if (it.radio === 'repr') return this.representation === it.value
      if (it.radio === 'measure') return this.measureMode === it.value
      if (it.radio === 'theme') return (currentTheme() || 'light') === it.value
      if (it.toggle) return !!this[it.toggle]
      return false
    },
    // ===== 左侧工具栏 =====
    toolActive(t) {
      if (t.menu === 'ring') return false                    // 「更多环」只是打开菜单，不算选中
      if (t.base === 'ring') return this.tool === 'ring' && !!this.armRing && this.armRing.id === t.ring
      if (t.base) return this.tool === t.base && this.bondOrder === t.order
      return this.tool === t.id
    },
    async activateTool(t, ev) {
      this.tool = t.base || t.id
      if (t.order) this.bondOrder = t.order
      if (t.ring) this.armRing = this.ringOf(t.ring)
      if (t.menu) {
        this.openToolMenu(t.menu, ev && ev.currentTarget)
        if (t.menu === 'ring') { await this.ensureRings(); if (!this.armRing && this.rings.length) this.armRing = this.ringOf(this.rings[0].id) }
      } else {
        this.toolMenu = ''
      }
    },
    ringOf(id) {
      const r = this.rings.find(x => x.id === id)
      return r ? { id: r.id, label: r.label } : { id, label: id }
    },
    // 环模板列表兜底：初次加载异常时按需再取一次（避免二级菜单是空的）
    async ensureRings() {
      if (this.rings.length) return true
      try {
        const r = await fetch(`${this.backendUrl}/api/mol/presets`)
        const d = await r.json()
        this.rings = d.rings || []
      } catch (e) {
        this.addLog($tr('读取环模板失败: {0}', { 0: e.message }), '#ff6b6b')
      }
      return this.rings.length > 0
    },
    openToolMenu(id, el) {
      const r = el && el.getBoundingClientRect ? el.getBoundingClientRect() : { left: 60, top: 120, right: 100 }
      this.menuPos = { left: Math.round(r.right + 4), top: Math.round(r.top) }
      this.toolMenu = this.toolMenu === id ? '' : id
      this.openMenu = ''
      this._menuAt = Date.now()
    },
    setBondOrder(o) {
      this.bondOrder = o
      this.tool = 'bond'
      this.toolMenu = ''
      const b = (this.mol.bonds || [])[this.bondSel]
      if (b) this.onCycleBond({ a: b.a, b: b.b, order: o })
    },
    setChargeDelta(d) {
      this.chargeDelta = d
      this.tool = 'charge'
      this.toolMenu = ''
    },
    setSelectMode(mode) {
      this.selectMode = mode
      this.tool = 'select'
      this.toolMenu = ''
    },
    zoomCanvas(f) {
      if (this.$refs.canvas && this.$refs.canvas.zoomBy) this.$refs.canvas.zoomBy(f)
    },
    deleteSelection() {
      const picked = (this.selectedAtoms && this.selectedAtoms.length)
        ? this.selectedAtoms.slice()
        : (this.selected !== null ? [this.selected] : [])
      if (picked.length) {
        // 从大到小删，避免序号重排
        const ops = picked.sort((a, b) => b - a).map(i => ({ op: 'remove_atom', payload: { index: i } }))
        this.editMany(ops, ops.length > 1 ? $tr('已删除 {0} 个原子', { 0: ops.length }) : '')
        return
      }
      if (this.bondSel >= 0) this.removeBond()
    },

    // ===== 文件列表 =====
    async refreshList() {
      if (!this.folder) return
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/list`, { folder: this.folder })
      if (!ok) {
        this.files = []
        this.addLog($tr('读取目录失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      this.files = data.files || []
      this.addLog($tr('找到 {0} 个分子文件', { 0: this.files.length }), '#87d2ff')
    },
    async chooseFolder() {
      let p
      try {
        p = await pickDirectory($tr('选择包含分子文件的文件夹'), this.folder)
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      if (!p) return
      this.folder = p
      await this.refreshList()
    },
    async useMolsDir() {
      this.folder = this.molsDir
      await this.refreshList()
    },
    newMolecule() {
      this.activeName = ''
      this.mol = { ...EMPTY_MOL }
      this.mol3d = null
      this.stale3d = false
      this.selected = null
      this.bondSel = -1
      this.saveName = ''
      this.desc = null
      this.charges = []
      this.dipole = null
      this.measurements = []
      this.undoStack = []
      this.redoStack = []
      this.armRing = null
      this.addLog($tr('已新建空白分子：在画布上单击放原子，从原子拖动即可画键'), '#87d2ff')
    },

    // ===== 打开 / 检索 =====
    async openFile(file) {
      if (this.busy) return
      this.busy = true
      this.addLog($tr('打开: {0}', { 0: file.name }), '#87d2ff')
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/open`, { path: file.path })
      this.busy = false
      if (!ok) {
        this.addLog($tr('打开失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      this.activeName = file.name
      this.undoStack = []
      this.redoStack = []
      this.measurements = []
      this.charges = []
      this.dipole = null
      this.desc = null
      this.saveName = data.name || file.name.replace(/\.[^.]+$/, '')
      this.applyMol(data)
      if (data.has3d) {
        this.mol3d = this.pick3d(data)
        this.stale3d = false
        await this.layout2dNow(true)              // 画布始终是干净的 2D 结构式
      } else {
        this.mol3d = null
        this.stale3d = false
        this.laid2d = true
        this.scheduleLiveSync()                   // 没有 3D 坐标 → 自动生成 3D 模型
      }
      this.addLog($tr('已载入 {0}：{1} 个原子 / {2} 个键{3}', {
        0: file.name, 1: data.n_atoms, 2: data.n_bonds, 3: data.note ? '（' + tNote(data.note) + '）' : ''
      }), '#7cfc00')
    },
    async fetchPubChem() {
      const q = (this.fetchQuery || '').trim()
      if (!q || this.busy) return
      this.busy = true
      this.addLog($tr('PubChem 检索: {0}（{1}）', { 0: q, 1: this.$t(this.fetchKindLabel()) }), '#87d2ff')
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/fetch`, { query: q, kind: this.fetchKind })
      this.busy = false
      if (!ok) {
        this.addLog($tr('检索失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      this.activeName = ''
      this.undoStack = []
      this.redoStack = []
      this.measurements = []
      this.charges = []
      this.dipole = null
      this.desc = null
      this.saveName = data.name || q
      this.applyMol(data)
      this.mol3d = null
      this.stale3d = false
      this.laid2d = true
      this.addLog($tr('已从 PubChem 载入 {0}（{1} 个原子）', { 0: data.name || q, 1: data.n_atoms }), '#7cfc00')
    },
    fetchKindLabel() {
      if (this.fetchKind === 'cid') return '按 CID'
      if (this.fetchKind === 'smiles') return '按 SMILES'
      return '按名称'
    },

    pick3d(data) {
      return {
        molblock: data.molblock || '',
        atoms: data.atoms || [],
        bonds: data.bonds || [],
        n_atoms: data.n_atoms || 0,
        n_bonds: data.n_bonds || 0,
        is3d: data.has3d !== undefined ? !!data.has3d : true
      }
    },
    applyMol(data, keepSelection = false) {
      const prevErr = this.validError
      this.validError = data.valid === false ? (data.valid_error || $tr('结构未通过价键检查')) : ''
      if (this.validError && this.validError !== prevErr) {
        this.addLog($tr('结构不合法：{0}', { 0: this.validError }), '#ff6b6b')
      }
      this.mol = {
        molblock: data.molblock !== undefined ? data.molblock : this.mol.molblock,
        atoms: data.atoms || [],
        bonds: data.bonds || [],
        formula: data.formula || '',
        mw: data.mw || 0,
        smiles: data.smiles || '',
        n_atoms: data.n_atoms || 0,
        n_bonds: data.n_bonds || 0,
        is3d: data.has3d !== undefined ? !!data.has3d : (data.is3d !== undefined ? !!data.is3d : this.mol.is3d),
        name: data.name || this.mol.name,
        noteRaw: data.note || '',
        charge: data.charge !== undefined && data.charge !== null ? data.charge : (this.mol.charge || 0),
        mult: data.mult || this.mol.mult || 1
      }
      if (!keepSelection) this.onSelectAtom(null)
      this.syncStore()
    },
    snapshot() {
      return JSON.parse(JSON.stringify({
        molblock: this.mol.molblock, atoms: this.mol.atoms, bonds: this.mol.bonds,
        formula: this.mol.formula, mw: this.mol.mw, smiles: this.mol.smiles,
        n_atoms: this.mol.n_atoms, n_bonds: this.mol.n_bonds,
        charge: this.mol.charge, mult: this.mol.mult, noteRaw: this.mol.noteRaw,
        validError: this.validError
      }))
    },
    pushHistory() {
      this.undoStack.push(this.snapshot())
      if (this.undoStack.length > 60) this.undoStack.shift()
      this.redoStack = []
    },
    restore(snap) {
      const validError = snap.validError || ''
      const molSnap = { ...snap }
      delete molSnap.validError
      this.mol = { ...this.mol, ...molSnap }
      this.validError = validError
      this.selected = null
      this.selectedAtoms = []
      this.bondSel = -1
      this.desc = null
      this.charges = []
      this.dipole = null
      this.stale3d = !!this.mol3d
      this.syncStore()
      this.scheduleLiveSync()          // 撤销/重做后 3D 跟着刷新
    },
    undo() {
      if (!this.undoStack.length) return
      this.redoStack.push(this.snapshot())
      this.restore(this.undoStack.pop())
      this.addLog($tr('已撤销'), '#87d2ff')
    },
    redo() {
      if (!this.redoStack.length) return
      this.undoStack.push(this.snapshot())
      this.restore(this.redoStack.pop())
      this.addLog($tr('已重做'), '#87d2ff')
    },
    onKey(e) {
      const tag = (e.target && e.target.tagName) || ''
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (e.key === 'Escape') {        this.openMenu = ''
        this.toolMenu = ''
        this.selected = null
        this.bondSel = -1
        if (this.tool === 'ring' || this.tool === 'erase') this.tool = 'bond'
        return
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault()
        if (e.shiftKey) this.redo(); else this.undo()
        return
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') { e.preventDefault(); this.redo(); return }
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (this.selected !== null) { e.preventDefault(); this.onDeleteAtom(this.selected); return }
        if (this.bondSel >= 0) { e.preventDefault(); this.removeBond() }
        return
      }
      // 悬停（或选中）原子 + 按字母键 = 改元素（小写=小序数元素，大写=大序数元素）
      if (!e.ctrlKey && !e.metaKey && !e.altKey && /^[A-Za-z]$/.test(e.key)) {
        const el = elementForKey(e.key)
        if (!el) return
        // 多选时整组一起改
        const picked = (this.hoverAtom !== null && this.hoverAtom !== undefined)
          ? [this.hoverAtom]
          : ((this.selectedAtoms && this.selectedAtoms.length) ? this.selectedAtoms : (this.selected !== null ? [this.selected] : []))
        const targets = picked.filter((i) => {
          const a = (this.mol.atoms || []).find(x => x.index === i)
          return a && a.symbol !== el
        })
        if (!targets.length) return
        e.preventDefault()
        if (targets.length === 1) this.onSetElement({ index: targets[0], element: el })
        else {
          this.editMany(targets.map(i => ({ op: 'set_element', payload: { index: i, element: el } })),
            $tr('已把 {0} 个原子改为 {1}', { 0: targets.length, 1: el }))
        }
      }
    },

    // ===== 视图 =====
    syncStore() {
      const store = useMoleculeStore()
      const use3d = this.saveFrom3d && this.mol3d && (this.mol3d.atoms || []).length
      store.put({
        molblock: use3d ? this.mol3d.molblock : this.mol.molblock,
        name: this.mol.name || this.saveName,
        atoms: use3d ? this.mol3d.atoms : this.mol.atoms,
        charge: this.mol.charge || 0,
        mult: this.mol.mult || 1,
        source: this.activeName
      })
    },
    onSelectAtom(idx) {
      if (idx === null || idx === undefined || idx === '') idx = null
      if (idx !== null && (idx < 0 || idx >= this.mol.n_atoms)) return
      this.selected = idx
      this.selectedAtoms = idx === null ? [] : [idx]
    },
    // 框选/曲线选：一次选中多个原子
    onSelectAtoms(list) {
      const valid = (list || []).filter(i => i >= 0 && i < this.mol.n_atoms)
      this.selectedAtoms = valid
      this.selected = valid.length ? valid[valid.length - 1] : null
      this.bondSel = -1
      if (valid.length > 1) this.addLog($tr('已选中 {0} 个原子', { 0: valid.length }), '#87d2ff')
    },
    onViewerSelect(idx) {
      if (this.measureMode) { this.pickForMeasure(idx); return }
      this.onSelectAtom(idx)
    },
    onSelectBond(i) {
      this.bondSel = (i === null || i === undefined || i === '') ? -1 : Number(i)
    },
    clearSelection() {
      this.selected = null
      this.selectedAtoms = []
      this.bondSel = -1
    },
    refit() {
      if (this.$refs.canvas) this.$refs.canvas.refit()
      if (this.$refs.viewer && this.$refs.viewer.resetView) this.$refs.viewer.resetView()
    },
    async cleanUp(silent = false) {
      return this.layout2dNow(silent)
    },
    async layout2dNow(silent = false) {
      if (!this.mol.molblock || this.busy) return false
      this.busy = true
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/layout2d`, { molblock: this.mol.molblock })
      this.busy = false
      if (!ok) {
        this.addLog($tr('整理结构失败: {0}', { 0: data.detail }), '#ff6b6b')
        return false
      }
      this.pushHistory()
      this.applyMol(data, true)
      this.laid2d = true
      this.$nextTick(() => this.$refs.canvas && this.$refs.canvas.refit())
      if (!silent) this.addLog($tr('已整理为理想 2D 结构'), '#7cfc00')
      return true
    },
    // 3D 浏览始终启用：结构一改就在后台重新生成 3D 模型（防抖）
    scheduleLiveSync() {
      if (!this.mol.n_atoms) {          // 空画布：清空 3D，别发请求
        if (this._liveTimer) { clearTimeout(this._liveTimer); this._liveTimer = null }
        this.mol3d = null
        this.stale3d = false
        this.syncing3d = false
        return
      }
      if (this._liveTimer) clearTimeout(this._liveTimer)
      this._liveTimer = setTimeout(() => { this.embedNow(true) }, 600)
    },

    // ===== 3D 模型 =====
    async embedNow(silent = false) {
      if (this.busy) return false
      // 画布被擦空：3D 区也跟着清空，不做无意义的生成
      if (!this.mol.n_atoms || !this.mol.molblock) {
        this.mol3d = null
        this.stale3d = false
        this.syncing3d = false
        return false
      }
      this.syncing3d = true
      this.busy = true
      if (!silent) this.addLog($tr('正在用 RDKit 生成合理的 3D 结构…'), '#87d2ff')
      // 大分子只做快速嵌入，避免每次编辑都跑力场优化
      const quick = (this.mol.n_atoms || 0) > 60
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/embed3d`,
        { molblock: this.mol.molblock, ff: 'MMFF94', optimize: !quick })
      this.busy = false
      this.syncing3d = false
      if (!ok) {
        this.addLog($tr('3D 生成失败: {0}', { 0: data.detail }), '#ff6b6b')
        return false
      }
      this.mol3d = this.pick3d(data)
      this.stale3d = false
      if (this.showCharges) await this.computeCharges(true)
      if (!silent) this.addLog($tr('3D 优化完成{0}', { 0: data.note ? '（' + tNote(data.note) + '）' : '' }), '#7cfc00')
      this.$nextTick(() => this.$refs.viewer && this.$refs.viewer.resetView && this.$refs.viewer.resetView())
      return true
    },
    optimize3d() { return this.embedNow(false) },
    async toggleCharges() {
      if (this.showCharges) {
        this.showCharges = false
        this.charges = []
        this.dipole = null
        return
      }
      if (!this.has3d) {
        this.addLog($tr('原子电荷需要 3D 模型：请等 3D 生成完成'), '#ffa500')
        return
      }
      this.showCharges = true
      await this.computeCharges()
    },

    // ===== 测量 =====
    measureLabel(type) {
      if (type === 'distance') return '距离'
      if (type === 'angle') return '键角'
      return '扭转角'
    },
    setMeasure(mode) {
      if (!this.has3d) {
        this.addLog($tr('测量需要 3D 模型：请先点「转换为 3D」'), '#ffa500')
        return
      }
      this.measureMode = this.measureMode === mode ? null : mode
      this.measurePicks = []
      if (this.measureMode) {
        this.addLog($tr('{0} 测量：请在 3D 模型上依次点击 {1} 个原子', {
          0: $tr(this.measureLabel(mode)), 1: MEASURE_NEED[mode]
        }), '#87d2ff')
      }
    },
    clearMeasure() {
      this.measurements = []
      this.measurePicks = []
      this.measureMode = null
      this.addLog($tr('已清除测量'), '#87d2ff')
    },
    pickForMeasure(idx) {
      const need = this.measureNeed
      if (!need) return
      this.measurePicks.push(idx)
      if (this.measurePicks.length >= need) {
        const picked = this.measurePicks.slice(0, need)
        const m = this.computeMeasurement(this.measureMode, picked)
        if (m) {
          this.measurements.push(m)
          this.addLog($tr('{0} = {1}', { 0: $tr(this.measureLabel(m.type)), 1: m.text }), '#7cfc00')
        }
        this.measurePicks = []
      }
    },
    computeMeasurement(type, idxs) {
      const src = this.mol3d && (this.mol3d.atoms || []).length ? this.mol3d.atoms : this.mol.atoms
      const P = idxs.map(i => (src || []).find(a => a.index === i)).filter(Boolean)
      if (P.length !== idxs.length) return null
      if (type === 'distance') {
        const d = len(sub(P[0], P[1]))
        return { type, atoms: idxs, value: d, text: d.toFixed(3) + ' Å' }
      }
      if (type === 'angle') {
        const a = angleDeg(P[0], P[1], P[2])
        return { type, atoms: idxs, value: a, text: a.toFixed(2) + '°' }
      }
      const t = torsionDeg(P[0], P[1], P[2], P[3])
      return { type, atoms: idxs, value: t, text: t.toFixed(2) + '°' }
    },

    // ===== 计算（化学数据 / 电荷） =====
    async loadDescriptors() {
      if (!this.mol.molblock || this.busy) return
      this.busy = true
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/descriptors`, { molblock: this.mol.molblock })
      this.busy = false
      if (!ok) {
        this.addLog($tr('读取化学数据失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      this.desc = data
      this.addLog($tr('已获取化学数据（{0}）', { 0: data.formula || '' }), '#7cfc00')
    },
    async computeCharges(quiet = false) {
      if (!this.mol.molblock || this.busy) return
      if (!this.has3d) {
        this.addLog($tr('原子电荷着色需要 3D 模型：请先点「转换为 3D」'), '#ffa500')
        return
      }
      this.busy = true
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/charges`, { molblock: this.mol.molblock })
      this.busy = false
      if (!ok) {
        this.addLog($tr('计算电荷失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      this.charges = data.charges || []
      this.dipole = data.dipole || null
      if (!quiet) {
        const d = this.dipole ? `，偶极 ${Number(this.dipole.magnitude).toFixed(2)} D` : ''
        this.addLog($tr('已用 Gasteiger 计算原子电荷{0}', { 0: d }), '#7cfc00')
      }
    },

    // ===== 导出（对标 MolView 的导出菜单） =====
    async pickExportDir() {
      try {
        return await pickDirectory($tr('选择导出目录'), this.molsDir || this.folder)
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
        return ''
      }
    },
    exportName() { return (this.saveName || this.mol.name || 'molecule').trim() || 'molecule' },
    async saveFileTo(folder, filename, content, base64) {
      const body = { folder, filename }
      if (base64) body.content_base64 = base64
      else body.content = content
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/save-file`, body)
      if (!ok) {
        this.addLog($tr('导出失败: {0}', { 0: data.detail }), '#ff6b6b')
        return false
      }
      this.addLog($tr('已导出 {0}', { 0: data.path }), '#7cfc00')
      return true
    },
    async export2d(fmt) {
      if (!this.mol.n_atoms) return
      const svg = this.$refs.canvas ? this.$refs.canvas.toSvg() : ''
      if (!svg) { this.addLog($tr('导出失败: 画布为空'), '#ff6b6b'); return }
      const dir = await this.pickExportDir()
      if (!dir) return
      if (fmt === 'svg') {
        await this.saveFileTo(dir, `${this.exportName()}.svg`, svg)
        return
      }
      try {
        const png = await this.rasterize(svg)
        await this.saveFileTo(dir, `${this.exportName()}.png`, null, png)
      } catch (e) {
        this.addLog($tr('导出失败: {0}', { 0: e.message }), '#ff6b6b')
      }
    },
    rasterize(svgText) {
      return new Promise((resolve, reject) => {
        const m = /width=['"](\d+(?:\.\d+)?)/.exec(svgText)
        const w = m ? Number(m[1]) : 800
        const blob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const img = new Image()
        img.onload = () => {
          try {
            const c = document.createElement('canvas')
            c.width = Math.max(200, Math.round(w * 2))
            c.height = Math.round(c.width * (img.height / Math.max(1, img.width)))
            const ctx = c.getContext('2d')
            ctx.fillStyle = '#ffffff'
            ctx.fillRect(0, 0, c.width, c.height)
            ctx.drawImage(img, 0, 0, c.width, c.height)
            URL.revokeObjectURL(url)
            resolve(c.toDataURL('image/png'))
          } catch (e) { reject(e) }
        }
        img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('SVG 转 PNG 失败')) }
        img.src = url
      })
    },
    async export3dPng() {
      const uri = this.$refs.viewer && this.$refs.viewer.pngURI ? this.$refs.viewer.pngURI() : ''
      if (!uri) { this.addLog($tr('导出失败: 3D 模型不可用'), '#ff6b6b'); return }
      const dir = await this.pickExportDir()
      if (!dir) return
      await this.saveFileTo(dir, `${this.exportName()}_3D.png`, null, uri)
    },
    async exportMol(use3d = false) {
      const src = use3d ? this.mol3d : this.mol
      if (!src || !src.molblock) {
        this.addLog($tr('导出失败: 没有可导出的结构'), '#ff6b6b')
        return
      }
      const dir = await this.pickExportDir()
      if (!dir) return
      await this.saveFileTo(dir, `${this.exportName()}${use3d ? '_3D' : ''}.mol`, src.molblock)
    },
    openExternal(kind) {
      const d = this.desc || {}
      let url = ''
      if (kind === 'nist') {
        if (d.inchi) url = `https://webbook.nist.gov/cgi/cbook.cgi?InChI=${encodeURIComponent(d.inchi)}`
        else if (d.smiles) url = `https://webbook.nist.gov/cgi/cbook.cgi?SMILES=${encodeURIComponent(d.smiles)}`
      } else {
        const q = d.inchikey || d.smiles || this.saveName
        if (!q) { this.addLog($tr('请先获取化学数据（得到 InChI/SMILES）后再打开外部链接'), '#ffa500'); return }
        url = `https://pubchem.ncbi.nlm.nih.gov/#query=${encodeURIComponent(q)}`
      }
      if (!url) { this.addLog($tr('缺少 InChI/SMILES，无法生成外部链接'), '#ffa500'); return }
      window.open(url, '_blank')
      this.addLog($tr('已打开外部链接: {0}', { 0: url }), '#87d2ff')
    },

    // ===== 编辑（统一走后端，保证价键/芳香性正确） =====
    async edit(op, payload = {}, label = '') {
      if (this.busy) return false
      if (op !== 'add_atom' && op !== 'add_ring' && !this.mol.molblock) return false
      this.busy = true
      const before = this.snapshot()
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/edit`,
        { molblock: this.mol.molblock, op, payload })
      this.busy = false
      if (!ok) {
        this.addLog($tr('编辑失败: {0}', { 0: data.detail }), '#ff6b6b')
        return false
      }
      this.undoStack.push(before)
      if (this.undoStack.length > 60) this.undoStack.shift()
      this.redoStack = []
      this.applyMol(data, true)
      this.laid2d = true
      this.desc = null
      if (this.charges.length) { this.charges = []; this.dipole = null }
      this.mark3dStale()
      if (data.note) this.addLog(tNote(data.note), '#87d2ff')
      if (label) this.addLog(label, '#7cfc00')
      return true
    },
    mark3dStale() {
      if (this.mol3d) this.stale3d = true
      this.scheduleLiveSync()
    },
    onAddAtom({ x, y }) {
      this.edit('add_atom', { element: this.elementChoice, x, y }, $tr('已放置 {0}', { 0: this.elementChoice }))
    },
    onSetElement({ index, element }) {
      this.edit('set_element', { index, element })
    },
    onAddBond({ a, b, order }) {
      this.edit('add_bond', { a, b, order: order || 1 })
    },
    // 拖动空白：一条新键（两端都是新原子）
    async onAddAtomChain({ x1, y1, x2, y2, order = 1 }) {
      if (this.busy) return
      const element = this.elementChoice
      const before = this.snapshot()
      this.busy = true
      const r1 = await this.postJson(`${this.backendUrl}/api/mol/edit`,
        { molblock: this.mol.molblock, op: 'add_atom', payload: { element, x: x1, y: y1 } })
      if (!r1.ok) { this.busy = false; this.addLog($tr('编辑失败: {0}', { 0: r1.data.detail }), '#ff6b6b'); return }
      const i1 = (r1.data.atoms || []).length - 1
      const r2 = await this.postJson(`${this.backendUrl}/api/mol/edit`,
        { molblock: r1.data.molblock, op: 'add_atom', payload: { element, x: x2, y: y2 } })
      if (!r2.ok) { this.busy = false; this.addLog($tr('编辑失败: {0}', { 0: r2.data.detail }), '#ff6b6b'); return }
      const i2 = (r2.data.atoms || []).length - 1
      const r3 = await this.postJson(`${this.backendUrl}/api/mol/edit`,
        { molblock: r2.data.molblock, op: 'add_bond', payload: { a: i1, b: i2, order } })
      this.busy = false
      if (!r3.ok) { this.addLog($tr('编辑失败: {0}', { 0: r3.data.detail }), '#ff6b6b'); return }
      this.pushSnapshot(before, r3.data)
    },
    // 键工具下单击原子：按「躲开已有键」的方向自动接一个新原子（连续的点击即可快速长链）
    async onExtendAtom({ index }) {
      if (this.busy) return
      const pos = freeBondPosition(this.mol.atoms, this.mol.bonds, index)
      if (!pos) return
      return this.onAddBondAtom({ x: pos.x, y: pos.y, from: index, order: this.bondOrder })
    },
    // 从原子拖到空白：长出新原子并连键
    async onAddBondAtom({ x, y, from, order = 1 }) {
      if (this.busy) return
      const element = this.elementChoice
      const before = this.snapshot()
      this.busy = true
      const r1 = await this.postJson(`${this.backendUrl}/api/mol/edit`,
        { molblock: this.mol.molblock, op: 'add_atom', payload: { element, x, y } })
      if (!r1.ok) { this.busy = false; this.addLog($tr('编辑失败: {0}', { 0: r1.data.detail }), '#ff6b6b'); return }
      const idx = (r1.data.atoms || []).length - 1
      const r2 = await this.postJson(`${this.backendUrl}/api/mol/edit`,
        { molblock: r1.data.molblock, op: 'add_bond', payload: { a: from, b: idx, order } })
      this.busy = false
      if (!r2.ok) { this.addLog($tr('编辑失败: {0}', { 0: r2.data.detail }), '#ff6b6b'); return }
      this.pushSnapshot(before, r2.data)
    },
    pushSnapshot(before, data) {
      this.undoStack.push(before)
      if (this.undoStack.length > 60) this.undoStack.shift()
      this.redoStack = []
      this.applyMol(data, true)
      this.laid2d = true
      this.desc = null
      this.mark3dStale()
      if (data.note) this.addLog(tNote(data.note), '#87d2ff')
    },
    onCycleBond({ a, b, order }) {
      this.edit('set_bond_order', { a, b, order })
    },
    onChargeAtom({ index, delta }) {
      const a = this.mol.atoms.find(t => t.index === index)
      const cur = (a && a.charge) || 0
      this.edit('set_charge', { index, charge: cur + delta })
    },
    onDeleteAtom(index) {
      if (index === null || index === undefined || index < 0) return
      // 多选时一次删掉整组
      if ((this.selectedAtoms || []).length > 1 && this.selectedAtoms.includes(index)) {
        return this.deleteSelection()
      }
      this.edit('remove_atom', { index })
    },
    onDeleteBond({ a, b }) {
      this.edit('remove_bond', { a, b })
    },
    // 环工具是「粘性」的：可连续放置多个环，Esc 或切回键工具退出
    onPlaceRing({ x, y, attach }) {
      const ring = this.armRing ? this.armRing.id : 'benzene'
      this.edit('add_ring', { ring, x, y, attach })
    },
    onMoveAtom({ index, x, y }) {
      const a = this.mol.atoms.find(t => t.index === index)
      this.edit('set_position', { index, x, y, z: a ? a.z || 0 : 0 })
    },
    removeBond() {
      const b = (this.mol.bonds || [])[this.bondSel]
      if (!b) return
      this.onDeleteBond({ a: b.a, b: b.b })
    },
    // 连续多个编辑操作合成一次（一次撤销），框选批量改元素/电荷/删除用
    async editMany(ops, label = '') {
      if (this.busy || !ops || !ops.length) return false
      if (!this.mol.molblock) return false
      this.busy = true
      const before = this.snapshot()
      let block = this.mol.molblock
      let last = null
      for (const o of ops) {
        const r = await this.postJson(`${this.backendUrl}/api/mol/edit`,
          { molblock: block, op: o.op, payload: o.payload || {} })
        if (!r.ok) {
          this.busy = false
          this.addLog($tr('编辑失败: {0}', { 0: r.data.detail }), '#ff6b6b')
          return false
        }
        block = r.data.molblock
        last = r.data
      }
      this.busy = false
      this.pushSnapshot(before, last)
      if (label) this.addLog(label, '#7cfc00')
      return true
    },
    // 元素调色板：只切换「新原子的元素」，不改动已有原子（改元素用悬停+字母键）
    pickElement(el) {
      this.elementChoice = el
    },
    // 环模板：选中后切到环工具，可连续放置（点画布放置 / 点原子稠合），Esc 退出
    pickRing(r) {
      this.armRing = { id: r.id, label: r.label }
      this.tool = 'ring'
      this.openMenu = ''
      this.toolMenu = ''
    },
    bumpCharge(delta) {
      const picked = (this.selectedAtoms && this.selectedAtoms.length) ? this.selectedAtoms : (this.selected !== null ? [this.selected] : [])
      if (!picked.length) return
      const ops = picked.map((i) => {
        const a = this.mol.atoms.find(t => t.index === i)
        const cur = (a && a.charge) || 0
        return { op: 'set_charge', payload: { index: i, charge: cur + delta } }
      })
      this.editMany(ops)
    },
    addHs() {
      this.edit('add_hs', {}, $tr('已加显式氢'))
    },
    removeHs() {
      this.edit('remove_hs', {}, $tr('已去掉显式氢'))
    },

    // ===== 保存 =====
    async ensureExplicitH(data) {
      if (!this.saveWithH || !data || !data.molblock) return data
      const hasImplicit = ((data.atoms) || []).some(a => (a.implicit_h || 0) > 0)
      if (!hasImplicit) return data
      const r = await this.postJson(`${this.backendUrl}/api/mol/edit`,
        { molblock: data.molblock, op: 'add_hs', payload: {} })
      if (!r.ok) {
        this.addLog($tr('加氢失败: {0}', { 0: r.data.detail }), '#ffa500')
        return data
      }
      return r.data
    },
    async saveMls() {
      if (this.saving || !this.mol.n_atoms) return
      const name = (this.saveName || '').trim()
      if (!name) {
        this.addLog($tr('请先输入分子名称'), '#ffa500')
        return
      }
      const use3d = !!(this.saveFrom3d && this.mol3d && this.mol3d.molblock)
      this.saving = true
      let src = use3d
        ? { molblock: this.mol3d.molblock, atoms: this.mol3d.atoms }
        : { molblock: this.mol.molblock, atoms: this.mol.atoms }
      const before = await this.ensureExplicitH(src)
      src = { molblock: before.molblock, atoms: before.atoms }
      if (use3d) {
        this.mol3d = { ...this.mol3d, molblock: src.molblock, atoms: src.atoms }
      } else {
        this.applyMol(before, true)
      }
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/save-mls`,
        { name, atoms: src.atoms })
      this.saving = false
      if (!ok) {
        this.addLog($tr('保存失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      this.mol.name = name
      this.addLog($tr('已保存 {0}（{1} 个原子，{2}）', {
        0: data.path, 1: data.n_atoms, 2: use3d ? $tr('3D 模型坐标') : $tr('2D 画布坐标')
      }), '#7cfc00')
      this.molsDir = data.dir || this.molsDir
      if (this.folder === this.molsDir) await this.refreshList()
    },
    async saveMlsAs() {
      let dir
      try {
        dir = await pickDirectory($tr('选择 .mls 保存目录'), this.molsDir)
      } catch (e) {
        this.addLog($tr('选择目录失败: {0}', { 0: e.message }), '#ff6b6b')
        return
      }
      if (!dir) return
      const use3d = !!(this.saveFrom3d && this.mol3d && this.mol3d.molblock)
      let src = use3d
        ? { molblock: this.mol3d.molblock, atoms: this.mol3d.atoms }
        : { molblock: this.mol.molblock, atoms: this.mol.atoms }
      const before = await this.ensureExplicitH(src)
      src = { molblock: before.molblock, atoms: before.atoms }
      const name = (this.saveName || 'molecule').trim()
      const { ok, data } = await this.postJson(`${this.backendUrl}/api/mol/save-mls`,
        { name, atoms: src.atoms, directory: dir })
      if (!ok) {
        this.addLog($tr('保存失败: {0}', { 0: data.detail }), '#ff6b6b')
        return
      }
      this.folder = dir
      await this.refreshList()
      this.addLog($tr('已保存 {0}', { 0: data.path }), '#7cfc00')
    },
    gotoInputGen() {
      this.syncStore()
      this.$router.push('/input-gen')
    }
  }
}
</script>

<style scoped>
.mv-menu { position: relative; }
.mv-menu-btn { border-radius: 0; }
.mv-menu-open { background: var(--c-selected); color: var(--c-selected-text); }
.mv-menu-panel {
  position: fixed;
  z-index: 200;
  min-width: 220px;
  max-height: 70vh;
  overflow-y: auto;
  background: var(--c-elev);
  border: 1px solid var(--c-border-strong);
  box-shadow: 2px 2px 6px rgba(0, 0, 0, 0.35);
  padding: 2px 0;
}
.mv-menu-item {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
  padding: 4px 10px;
  font-size: 12px;
  color: var(--c-text);
  cursor: pointer;
}
.mv-menu-item:hover { background: var(--c-selected); color: var(--c-selected-text); }
.mv-menu-sep { height: 1px; background: var(--c-border-soft); margin: 3px 0; }
.mv-panel-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--c-text-2);
  padding: 4px 8px 2px 8px;
}
.mv-warn {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 22px;
  padding: 0 8px;
  font-size: 11px;
  color: #ffffff;
  background: var(--c-danger);
  border-bottom: 1px solid var(--c-border-strong);
  flex-shrink: 0;
}
/* 顶部绘制工具栏（图标按钮） */
.mv-topbar {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 30px;
  padding: 0 6px;
  background: var(--c-bar);
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}
.mv-ibtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: transparent;
  border: 1px solid transparent;
  color: var(--c-text);
  cursor: pointer;
}
.mv-ibtn:hover:not(:disabled) { background: var(--c-hover); border-color: var(--c-border); }
.mv-ibtn:disabled { opacity: 0.35; cursor: default; }
.mv-ibtn-on { background: var(--c-selected); color: var(--c-selected-text); border-color: var(--c-border-strong); }
/* 左侧绘制工具栏（MolView 风格竖排图标） */
.mv-toolstrip {
  width: 32px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 3px 2px;
  background: var(--c-bar);
  border-right: 1px solid var(--c-border);
  overflow-y: auto;
}
.mv-tool {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--c-text);
  cursor: pointer;
  padding: 0;
}
.mv-tool:hover { background: var(--c-hover); border-color: var(--c-border); }
.mv-tool-on {
  background: var(--c-selected);
  color: var(--c-selected-text);
  border-color: var(--c-border-strong);
}
.mv-sub {
  position: absolute;
  right: 1px;
  bottom: 0;
  font-size: 7px;
  opacity: 0.8;
}
/* 右侧元素栏（MolView 风格竖排） */
.mv-palette {
  width: 30px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 3px 2px;
  background: var(--c-bar);
  border-left: 1px solid var(--c-border);
  overflow-y: auto;
}
.mv-el {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 22px;
  font-size: 12px;
  font-weight: 600;
  background: transparent;
  border: 1px solid transparent;
  color: var(--c-text);
  cursor: pointer;
  padding: 0;
  font-family: Arial, Helvetica, sans-serif;
}
.mv-el:hover { background: var(--c-hover); border-color: var(--c-border); }
.mv-el-on {
  background: var(--c-selected);
  color: var(--c-selected-text);
  border-color: var(--c-border-strong);
}
.mv-el:disabled { opacity: 0.45; cursor: default; }
/* 环模板缩略图按钮 */
.mv-thumb {
  width: 30px;
  height: 30px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
}
.mv-thumb:hover { background: var(--c-hover); border-color: var(--c-border); }
.mv-thumb-on { background: var(--c-selected); border-color: var(--c-border-strong); }
.mv-palette-sep {
  height: 1px;
  background: var(--c-border-soft);
  margin: 3px 0;
}
.mv-sep-v {
  width: 1px;
  height: 18px;
  background: var(--c-border-soft);
  flex-shrink: 0;
  margin: 0 2px;
}
</style>
