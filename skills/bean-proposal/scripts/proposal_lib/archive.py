"""zip 안 자료를 디스크에 풀지 않고 메모리에서 훑어본다.

집계 방식은 자료마다 다르므로 여기서는 "무엇이 들어 있나"만 알려 준다 (파일 목록, 시트·행 수·열 이름, 앞부분 몇 줄).
개인정보로 보이는 열은 값을 가리고 이름만 알려 준다. 집계는 에이전트가 그때그때 임시 스크립트로 한다.
"""
import csv
import io
import re
import zipfile

# 열 이름에 이런 말이 들어 있으면 값을 읽지 않는다 (수하인·연락처·주소 등)
PII = re.compile(r"(수하인|수취인|받는\s*분|수령인|이름|성명|연락|전화|휴대|핸드폰|tel|phone|mobile|주소|addr|이메일|e-?mail|주민|계좌)", re.I)


def _name(info):
    """한글 파일명이 깨진 zip(cp437 로 저장된 것)을 복원한다."""
    n = info.filename
    if not info.flag_bits & 0x800:
        try:
            n = n.encode("cp437").decode("cp949")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return n


def members(path):
    z = zipfile.ZipFile(path)
    return z, [(i, _name(i)) for i in z.infolist() if not i.is_dir()]


def _cell(v):
    return "" if v is None else str(v)[:60]


def _take_header(it):
    """제목·빈 줄 뒤에 머리글이 오는 시트가 많다. 첫 10줄 중 값이 가장 많이 찬 줄을 머리글로 보고, 그 뒤 줄부터 돌려준다."""
    buf = []
    for r in it:
        buf.append(r)
        if len(buf) >= 10:
            break
    best = max(range(len(buf)), key=lambda i: sum(c is not None and str(c).strip() != "" for c in buf[i]), default=None)
    if best is None:
        return [], iter(())
    import itertools
    return [_cell(c) for c in buf[best]], itertools.chain(buf[best + 1:], it)


def _sheet_summary(ws, rows):
    it = ws.iter_rows(values_only=True)
    header, it = _take_header(it)
    sample = []
    total = 1 if header else 0
    for r in it:
        if any(c is not None for c in r):
            total += 1
            if len(sample) < rows:
                sample.append([_cell(c) for c in r])
    pii = [i for i, h in enumerate(header) if PII.search(h)]
    for row in sample:
        for i in pii:
            if i < len(row):
                row[i] = "(가림)"
    return {"rows": total, "columns": header, "pii_columns": [header[i] for i in pii], "sample": sample}


def _xlsx_info(data, rows):
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    return {n: _sheet_summary(wb[n], rows) for n in wb.sheetnames}


def _csv_info(data, rows):
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            text = None
    if text is None:
        return {"error": "인코딩을 알 수 없는 csv"}
    r = list(csv.reader(io.StringIO(text)))
    header = r[0] if r else []
    pii = [i for i, h in enumerate(header) if PII.search(h)]
    sample = [list(x) for x in r[1:1 + rows]]
    for row in sample:
        for i in pii:
            if i < len(row):
                row[i] = "(가림)"
    return {"rows": len(r), "columns": header, "pii_columns": [header[i] for i in pii], "sample": sample}


def peek(path, member=None, rows=0):
    """member 가 없으면 파일 목록과 엑셀·csv 의 시트별 구조, 있으면 그 파일만 자세히."""
    z, ms = members(path)
    out = []
    for info, name in ms:
        if member and member not in name:
            continue
        ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
        item = {"name": name, "kb": round(info.file_size / 1024, 1)}
        try:
            if ext in ("xlsx", "xlsm"):
                item["sheets"] = _xlsx_info(z.read(info), rows)
            elif ext == "csv":
                item["table"] = _csv_info(z.read(info), rows)
            elif ext in ("xls", "doc", "ppt", "hwp"):
                item["note"] = "옛 형식: 메모리로 못 읽음. 해당 앱이 필요하면 사용자 승인 후 임시 폴더에 풀어 읽는다"
        except Exception as e:
            item["error"] = f"{type(e).__name__}: {str(e)[:120]}"
        out.append(item)
    return out


def _bucket(v, how):
    """날짜로 보이는 값을 월·연으로 묶는다 (datetime, 2026-03-05, 20260305, 2026.03.05)."""
    import datetime
    if how == "none" or v is None:
        return "" if v is None else str(v)
    if isinstance(v, (datetime.datetime, datetime.date)):
        y, m = v.year, v.month
    else:
        m_ = re.match(r"^\s*(\d{4})[-./]?(\d{2})", str(v))
        if not m_:
            return str(v)
        y, m = int(m_.group(1)), int(m_.group(2))
    return f"{y}" if how == "year" else f"{y}-{m:02d}"


def pivot(path, member, sheet, group, sums, bucket="none"):
    """한 시트를 열 이름 기준으로 묶어 건수와 합계를 낸다. 열 이름은 시트 첫 줄(머리글) 그대로 쓴다."""
    from openpyxl import load_workbook
    z, ms = members(path)
    hit = [(i, n) for i, n in ms if member in n]
    if len(hit) != 1:
        return {"error": f"member 가 {len(hit)}개와 맞습니다: {[n for _, n in hit][:5]}"}
    wb = load_workbook(io.BytesIO(z.read(hit[0][0])), read_only=True, data_only=True)
    if sheet not in wb.sheetnames:
        return {"error": f"시트가 없습니다. 있는 시트: {wb.sheetnames}"}
    it = wb[sheet].iter_rows(values_only=True)
    header, it = _take_header(it)
    for c in [group] + sums:
        if c not in header:
            return {"error": f"열이 없습니다: {c}. 있는 열: {header}"}
        if PII.search(c):
            return {"error": f"개인정보로 보이는 열은 집계하지 않습니다: {c}"}
    gi, si = header.index(group), [header.index(c) for c in sums]
    acc, skipped = {}, 0
    for r in it:
        if not any(c is not None for c in r):
            continue
        k = _bucket(r[gi] if gi < len(r) else None, bucket)
        a = acc.setdefault(k, {"건수": 0, **{c: 0.0 for c in sums}})
        a["건수"] += 1
        for c, i in zip(sums, si):
            v = r[i] if i < len(r) else None
            if isinstance(v, (int, float)):
                a[c] += v
            else:
                skipped += 1
    rows = [{group: k, **{c: (round(v, 2) if isinstance(v, float) else v) for c, v in a.items()}} for k, a in sorted(acc.items(), key=lambda x: str(x[0]))]
    return {"member": hit[0][1], "sheet": sheet, "group": group, "bucket": bucket, "sums": sums, "rows": rows,
            "non_numeric_cells": skipped, "note": "숫자가 아닌 칸은 합계에서 빠짐. 단위(BOX·EA·PLT)는 열마다 다르니 합치기 전에 환산 기준을 확인"}
