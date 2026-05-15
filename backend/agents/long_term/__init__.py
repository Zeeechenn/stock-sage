"""
长期分析师团 first batch

三个分析师周频运行，输出每只股票的「长期标签」（值得持有/估值偏高/观望/规避），
由风险经理作为硬约束影响短期信号。
"""
from backend.agents.long_term.base import LongTermReport, LongTermLabel
from backend.agents.long_term.piotroski_analyst import analyze as piotroski_analyze
from backend.agents.long_term.jingqi_analyst import analyze as jingqi_analyze
from backend.agents.long_term.a_teacher_analyst import analyze as a_teacher_analyze
from backend.agents.long_term.team import LongTermTeam
from backend.agents.long_term.storage import (
    save_label,
    get_active_label,
    bulk_get_labels,
)

__all__ = [
    "LongTermReport",
    "LongTermLabel",
    "piotroski_analyze",
    "jingqi_analyze",
    "a_teacher_analyze",
    "LongTermTeam",
    "save_label",
    "get_active_label",
    "bulk_get_labels",
]
