import quopri
import re
from pypinyin import Style, pinyin

# 常见中国多音字姓氏映射
SURNAME_OVERRIDES = {
    '单': 'shan',
    '解': 'xie',
    '查': 'zha',
    '区': 'ou',
    '朴': 'piao',
    '曾': 'zeng',
    '缪': 'miao',
    '仇': 'qiu',
    '秘': 'bi',
    '冼': 'xian',
}


class PhoneticGenerator:
    """提取 iOS VCF 联系人姓名，生成拼音与 T9 检索昵称"""

    def __init__(self, filename='contacts.vcf', output_filename='contacts_t9.vcf'):
        self.filename = filename
        self.output_filename = output_filename

    def _decode_vcard_value(self, line_or_value: str) -> str:
        """解析并解码可能存在的 Quoted-Printable 字符"""
        if 'ENCODING=QUOTED-PRINTABLE' in line_or_value.upper():
            # 提取编码内容并还原为 UTF-8
            raw_val = line_or_value.split(':', 1)[-1].strip()
            decoded_bytes = quopri.decodestring(raw_val.encode('ascii', errors='ignore'))
            return decoded_bytes.decode('utf-8', errors='replace')
        elif ':' in line_or_value:
            return line_or_value.split(':', 1)[-1].strip()
        return line_or_value.strip()

    def _clean_name(self, name: str) -> str:
        """清洗括号备注与前缀标签"""
        if not name:
            return ''
        name = re.sub(r'[（(【\[].*?[）)】\]]', '', name)
        if '-' in name:
            name = name.split('-')[-1]
        return name.strip()

    def _extract_name_parts(self, n_line: str):
        """准确提取姓与名（兼容转义与编码）"""
        decoded_val = self._decode_vcard_value(n_line)
        # 兼容转义分号
        parts = re.split(r'(?<!\\);', decoded_val)
        last_name = parts[0].replace(r'\;', ';').strip() if len(parts) > 0 else ''
        first_name = parts[1].replace(r'\;', ';').strip() if len(parts) > 1 else ''
        return self._clean_name(last_name), self._clean_name(first_name)

    def _get_phonetic_tokens(self, text: str, is_surname: bool = False):
        """转换汉字拼音（处理姓氏多音字）"""
        tokens = []
        for i, char in enumerate(text):
            if is_surname and i == 0 and char in SURNAME_OVERRIDES:
                tokens.append(SURNAME_OVERRIDES[char].capitalize())
            else:
                py_res = pinyin(char, style=Style.NORMAL)
                if py_res and py_res[0]:
                    tokens.append(py_res[0][0].capitalize())
                else:
                    tokens.append(char)
        return tokens

    def _generate_nickname(self, last_name: str, first_name: str) -> str:
        """
        生成适用于 T9 的 NICKNAME：
        组合为 'ZhangSan ZS'（支持全拼与简拼即时检索）
        """
        tokens = []
        if last_name:
            tokens.extend(self._get_phonetic_tokens(last_name, is_surname=True))
        if first_name:
            tokens.extend(self._get_phonetic_tokens(first_name, is_surname=False))

        if not tokens:
            return ''

        full_pinyin = ''.join(tokens)
        initials = ''.join([t[0].upper() for t in tokens if t])

        # 如果全拼和首字母相同（纯英文联系人），只保留一个
        if full_pinyin.upper() == initials:
            return full_pinyin
        return f"{full_pinyin} {initials}"

    def _process_vcard_block(self, block_lines):
        n_idx = None
        n_line = None

        for idx, line in enumerate(block_lines):
            if re.match(r'^(?:[^:]*\.)?N(?:;[^:]*)?:', line, re.IGNORECASE):
                n_idx = idx
                n_line = line
                break

        if n_line is None:
            return block_lines

        last_name, first_name = self._extract_name_parts(n_line)
        nickname_val = self._generate_nickname(last_name, first_name)

        if not nickname_val:
            return block_lines

        # 检查是否已有 NICKNAME 行
        nickname_idx = None
        for idx, line in enumerate(block_lines):
            if re.match(r'^(?:[^:]*\.)?NICKNAME(?:;[^:]*)?:', line, re.IGNORECASE):
                nickname_idx = idx
                break

        newline = '\r\n' if n_line.endswith('\r\n') else '\n'

        if nickname_idx is not None:
            block_lines[nickname_idx] = f"NICKNAME:{nickname_val}{newline}"
        else:
            block_lines.insert(n_idx + 1, f"NICKNAME:{nickname_val}{newline}")

        return block_lines

    def convert(self):
        with open(self.filename, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        updated_lines = []
        i = 0
        total = len(lines)

        while i < total:
            line = lines[i]
            if line.strip().upper().startswith('BEGIN:VCARD'):
                block = []
                while i < total:
                    block.append(lines[i])
                    if lines[i].strip().upper().startswith('END:VCARD'):
                        i += 1
                        break
                    i += 1
                updated_lines.extend(self._process_vcard_block(block))
            else:
                updated_lines.append(line)
                i += 1

        with open(self.output_filename, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
