"""Multiwfn 引用说明（使用外部 Multiwfn 功能前必须让用户确认）

正文优先取 example 目录里的原始说明文件；打包后 example 不会进 resources，
所以这里同时内嵌一份完全相同的文本，保证任何情况下都拿得到。
"""
import os
from typing import List

# example 目录里的原始文件（仅用于展示来源；内容已内嵌）
CITATION_FILENAME = '提醒：使用Multiwfn发表文章(包括代算)需要在正文里引用程序原文.txt'

# 只要用了 Multiwfn 的任何功能，这两篇必须出现在正文里
MUST_CITE = [
    'Tian Lu, Feiwu Chen, J. Comput. Chem., 33, 580-592 (2012)   DOI: 10.1002/jcc.22885',
    'Tian Lu, J. Chem. Phys., 161, 082503 (2024)   DOI: 10.1063/5.0216272',
]

# 空穴-电子分析（sobereva.com/434）要求额外引用的一篇
HOLE_ELECTRON_CITE = [
    'Tian Lu, Carbon, 165, 461-467 (2020)   DOI: 10.1016/j.carbon.2020.05.023'
    '（空穴-电子分析，做该分析时也请引用）',
]

LINKS = [
    {'label': 'Multiwfn 主页 / 下载', 'url': 'http://sobereva.com/multiwfn'},
    {'label': 'How to cite Multiwfn（完整引用说明见程序包内 PDF）', 'url': 'http://sobereva.com/multiwfn'},
    {'label': 'Multiwfn 中文论坛（计算化学公社）', 'url': 'http://bbs.keinsci.com'},
    {'label': 'Multiwfn English forum', 'url': 'http://sobereva.com/wfnbbs'},
]

BODY = """使用了Multiwfn的文章里不引用或错误地引用Multiwfn程序的现象极为严重（尤其是在中国用户的文章中）！特此强调：

在研究中无论使用Multiwfn的哪个功能，在发表的文章的正文中都 必 须 对Multiwfn进行正确引用，这是最基本的学术道德规范。对Multiwfn的引用是在其程序下载页面里显示的使用条款（license）里明确注明的，不恰当引用相当于侵权使用，程序开发者有权要求出版社对文章进行撤稿处理。

最全面、合理的引用Multiwfn程序及其作者的相关工作的说明见Multiwfn程序包中的How to cite Multiwfn.pdf文档。如果你发表的使用了Multiwfn的文章中连此文档中提到的J. Comput. Chem., 33, 580-592 (2012)和J. Chem. Phys., 161, 082503 (2024)这两篇必须引的Multiwfn原文都没引用的话，将会被列入Multiwfn黑名单，并禁止在未来使用Multiwfn。

请在文章正文里提及和引用Multiwfn，而不要只放到补充材料里，否则不仅读者难以注意到，而且也不会被纳入引用的统计。

Multiwfn允许用于给别人代算时使用，但必须主动告诉对方在文章正文中需要引用Multiwfn程序。如果对方不肯这么引用，就不要给对方代算！

开发Multiwfn花费了巨大精力和心血，恰当引用Multiwfn原文及作者的相关文章是对Multiwfn这个完全免费、不懈开发的程序的开发最好的支持！

---------
另：

如果有Multiwfn使用上的问题，欢迎到http://bbs.keinsci.com的“波函数分析与Multiwfn”版块发帖咨询，开发者会非常及时回复（通常在24小时内回复）。也欢迎在Multiwfn英文论坛http://sobereva.com/wfnbbs上用英语发帖求助、和外国Multiwfn用户交流。开发者不在其它任何其它中文论坛里解答Multiwfn的使用问题。

初次接触Multiwfn者请务必阅读《Multiwfn入门tips》（http://sobereva.com/167）。《Multiwfn FAQ》（http://sobereva.com/452）也非常重要，强烈建议完整过目一遍。

---------

Multiwfn的版权信息：
在开始使用Multiwfn前，用户必须阅读并且接受以下条款
(a)目前Multiwfn是对学术用户和商业用户都完全开源免费的程序，任何人都可以向他人免费传播原版或者其自己的修改版的Multiwfn程序
(b)Multiwfn可以作为商业程序中的一个免费组件发布。售卖修改版Multiwfn也不是不可以，但必须事先获得Multiwfn开发者（卢天）的同意
(c)如果Multiwfn在你的研究中被使用，或者你自己写的代码里利用了Multiwfn中的代码，至少要在发表的文章中引用Multiwfn的原文J. Comput. Chem., 33, 580-592 (2012)和J. Chem. Phys., 161, 082503 (2024)
(d)Multiwfn开发者不保证Multiwfn计算结果的正确性，也不对因为使用Multiwfn给出的结果所导致的任何后果负责。（但开发者总会尽最大努力保证程序计算结果的正确性）
"""


def project_root() -> str:
    root = os.environ.get('MLS_PROJECT_ROOT')
    if not root:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    return root


def citation_source_file() -> str:
    """example 里的原始说明文件（找不到返回空串）"""
    p = os.path.join(project_root(), 'example', CITATION_FILENAME)
    return p if os.path.isfile(p) else ''


def citation_payload(kind: str = '', multiwfn_exe: str = '') -> dict:
    """给界面的引用说明。kind='hole-electron' 时额外带上该分析要求引用的一篇。"""
    src = citation_source_file()
    body = BODY
    if src:
        try:
            with open(src, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read().strip()
            if len(text) > 200:            # 文件被改坏时仍用内嵌文本
                body = text
        except OSError:
            pass
    must = list(MUST_CITE)
    extra: List[str] = []
    if kind == 'hole-electron':
        extra = list(HOLE_ELECTRON_CITE)
    pdf = ''
    if multiwfn_exe and os.path.isfile(multiwfn_exe):
        cand = os.path.join(os.path.dirname(multiwfn_exe), 'How to cite Multiwfn.pdf')
        if os.path.isfile(cand):
            pdf = cand
    return {'kind': kind, 'title': '使用 Multiwfn 必须在文章正文中引用其原文',
            'must_cite': must, 'extra_cite': extra, 'body': body, 'links': LINKS,
            'source': src, 'pdf': pdf}
