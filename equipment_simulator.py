"""무작위 장비의 등급·옵션·가격 분포를 반복 분석합니다."""

from __future__ import annotations

import argparse
import csv
import os
import random
from collections import Counter, defaultdict
from statistics import mean

import data
from models import EQUIPMENT_RARITIES, RARITY_NAMES_KR


def run_analysis(samples_per_level: int = 5000, seed: int = 20260914):
    random.seed(seed)
    grouped = defaultdict(list)
    rarity_counts = Counter()
    affix_counts = Counter()

    for level in range(1, 9):
        for _ in range(samples_per_level):
            equipment = data.generate_random_equipment(level)
            grouped[(level, equipment.rarity)].append(equipment)
            rarity_counts[equipment.rarity] += 1
            if equipment.special_effect:
                affix_counts.update(equipment.special_effect.split("/"))

    rows = []
    for level in range(1, 9):
        for rarity in EQUIPMENT_RARITIES:
            items = grouped[(level, rarity)]
            rows.append({
                "level": level,
                "rarity": rarity,
                "rarity_kr": RARITY_NAMES_KR[rarity],
                "count": len(items),
                "rate_within_level": len(items) / samples_per_level,
                "avg_price": mean(item.price for item in items) if items else 0,
                "avg_affix_count": mean(
                    len(item.special_effect.split("/")) if item.special_effect else 0
                    for item in items
                ) if items else 0,
            })
    return rows, rarity_counts, affix_counts


def write_outputs(output_dir: str, samples_per_level: int, seed: int) -> None:
    rows, rarity_counts, affix_counts = run_analysis(samples_per_level, seed)
    os.makedirs(output_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, "equipment_distribution.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    total = samples_per_level * 8
    expected = dict(zip(
        EQUIPMENT_RARITIES, data.RARITY_WEIGHTS,
    ))
    lines = [
        "# 무작위 장비 분포 분석",
        "",
        f"- 레벨별 생성 횟수: {samples_per_level:,}회",
        f"- 총 생성 장비: {total:,}개",
        f"- 난수 시드: {seed}",
        "",
        "## 등급 분포",
        "",
        "| 등급 | 설정 확률 | 관측 확률 | 평균 옵션 수 |",
        "|---|---:|---:|---:|",
    ]
    for rarity in EQUIPMENT_RARITIES:
        selected = [row for row in rows if row["rarity"] == rarity]
        lines.append(
            f"| {RARITY_NAMES_KR[rarity]} | {expected[rarity]:.1%} | "
            f"{rarity_counts[rarity] / total:.1%} | "
            f"{mean(row['avg_affix_count'] for row in selected):.1f} |"
        )

    lines += [
        "",
        "## 옵션 출현 횟수",
        "",
        "| 옵션 | 횟수 |",
        "|---|---:|",
    ]
    for affix, count in sorted(affix_counts.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"| {affix} | {count:,} |")
    lines += [
        "",
        "등급은 설정 확률에 따라 결정되며 일반 0개, 고급 1개, 희귀 2개, 영웅 3개, 전설 4개의 서로 다른 옵션이 붙음.",
    ]

    report_path = os.path.join(output_dir, "equipment_distribution_report.md")
    with open(report_path, "w", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    print(f"분석 완료: {report_path}")
    print(f"상세 데이터: {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="무작위 장비 등급·옵션 분포 분석")
    parser.add_argument("--samples", type=int, default=5000, help="레벨별 생성 횟수")
    parser.add_argument("--seed", type=int, default=20260914, help="난수 시드")
    parser.add_argument("--output-dir", default="equipment_results", help="결과 폴더")
    args = parser.parse_args()
    if args.samples <= 0:
        parser.error("--samples는 1 이상이어야 합니다.")
    write_outputs(args.output_dir, args.samples, args.seed)


if __name__ == "__main__":
    main()
