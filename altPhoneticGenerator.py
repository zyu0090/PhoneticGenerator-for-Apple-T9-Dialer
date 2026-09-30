import re
from pinyin import PinYin


class PhoneticGenerator:
    """处理 iPhone 联系人 VC 格式的转换，提取拼音并添加到字段中"""

    def __init__(self, filename='contacts.vcf'):
        """
        初始化 PhoneticConvert 对象

        :param filename: VCF 文件的路径，默认为 'contacts.vcf'
        """
        self.filename = filename
        self.py_engine = PinYin()
        self.py_engine.load_word()

    def convert(self):
        """
        将 VCF 文件中的联系人姓名转换为拼音简拼，并写入 NICKNAME 字段。
        如果原 vCard 已有 NICKNAME，则直接替换原有值；否则新增。
        """
        contact_lines = self._read_file()
        updated_contact = []
        i = 0
        total = len(contact_lines)

        while i < total:
            line = contact_lines[i]

            # 按 vCard 块处理，确保能先知道该联系人是否已有 NICKNAME
            if line.strip().upper().startswith('BEGIN:VCARD'):
                block = []
                while i < total:
                    block.append(contact_lines[i])
                    if contact_lines[i].strip().upper().startswith('END:VCARD'):
                        i += 1
                        break
                    i += 1
                updated_contact.extend(self._process_vcard_block(block))
            else:
                updated_contact.append(line)
                i += 1

        self._write_file(updated_contact)

    def _process_vcard_block(self, block_lines):
        """处理单个 vCard 块：计算拼音简拼，更新或插入 NICKNAME。"""
        n_index = None
        n_line = None

        for idx, line in enumerate(block_lines):
            if re.match(r'^(?:[^:]*\.)?N(?:;[^:]*)?:', line, re.IGNORECASE):
                n_index = idx
                n_line = line
                break

        if n_line is None:
            return block_lines

        last_name = self._extract_name_part(n_line, part='last')
        first_name = self._extract_name_part(n_line, part='first')

        if last_name:
            last_name = self._clean_name(last_name)
        if first_name:
            first_name = self._clean_name(first_name)

        full_name = ''
        if last_name:
            full_name += last_name
        if first_name:
            full_name += first_name

        if not full_name:
            return block_lines

        phonetic_name = self._convert_to_phonetic(full_name)
        if not phonetic_name:
            return block_lines

        nickname_indexes = [
            idx for idx, line in enumerate(block_lines)
            if re.match(r'^(?:[^:]*\.)?NICKNAME(?:;[^:]*)?:', line, re.IGNORECASE)
        ]

        if nickname_indexes:
            # 已有 NICKNAME：直接替换原有值，不新增
            for idx in nickname_indexes:
                block_lines[idx] = self._replace_nickname_value(
                    block_lines[idx], phonetic_name
                )
            return block_lines

        # 没有 NICKNAME：在 N 行后插入
        newline = '\n'
        if n_line.endswith('\r\n'):
            newline = '\r\n'
        elif n_line.endswith('\n'):
            newline = '\n'

        block_lines.insert(n_index + 1, f"NICKNAME:{phonetic_name}{newline}")
        return block_lines

    def _read_file(self):
        """读取 VCF 文件并返回文件中的每一行"""
        with open(self.filename, 'r', encoding='utf-8') as f:
            return f.readlines()

    def _write_file(self, updated_contact):
        """将更新后的联系人信息写回到 VCF 文件"""
        with open(self.filename, 'w', encoding='utf-8') as fout:
            fout.writelines(updated_contact)

    def _extract_name_part(self, line, part='last'):
        """
        从联系人信息中提取姓或名

        :param line: VCF 文件中的一行
        :param part: 提取部分，'last' 为姓，'first' 为名
        :return: 姓或名，如果未找到则返回 None
        """
        if ':' not in line:
            return None

        value = line.split(':', 1)[1].strip()
        parts = value.split(';')

        if part == 'last':
            return parts[0] if parts else None
        else:
            return parts[1] if len(parts) > 1 else None

    def _clean_name(self, name):
        """
        清洗姓名：
        1. 去除所有括号（中英文）及其内部内容；
        2. 去除连字符 '-' 及其之前的所有内容（保留最后一个 '-' 之后的部分）。

        :param name: 原始姓或名字符串
        :return: 清洗后的字符串
        """
        if not name:
            return name

        name = re.sub(r'[（(【\[].*?[）)】\]]', '', name)

        if '-' in name:
            name = name.split('-')[-1]

        return name.strip()

    def _replace_nickname_value(self, line, new_value):
        """替换 NICKNAME 行的值，保留属性名、参数和换行符。"""
        match = re.match(
            r'^((?:[^:]*\.)?NICKNAME(?:;[^:]*)?:)(.*?)(\r?\n)?$',
            line,
            re.IGNORECASE
        )
        if not match:
            return line

        prefix = match.group(1)
        newline = match.group(3) or ''
        return f"{prefix}{new_value}{newline}"

    def _convert_to_phonetic(self, name):
        """
        将汉字转换为拼音简拼：
        取每个汉字拼音的首字母并大写。

        例如：张三 -> ZS
             欧阳娜娜 -> OYNN

        :param name: 姓或名
        :return: 转换后的拼音简拼字符串
        """
        pinyin_list = self.py_engine.hanzi2pinyin(name)

        initials = []
        for item in pinyin_list:
            if not item:
                continue

            # 兼容多音字可能返回 "zhang,san" 这类情况，只取第一个拼音
            first_pinyin = item.split(',')[0].strip()
            if first_pinyin:
                initials.append(first_pinyin[0].upper())

        return ''.join(initials)


if __name__ == '__main__':
    filename = 'contacts.vcf'
    generator = PhoneticGenerator(filename)
    generator.convert()