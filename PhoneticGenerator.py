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
        """将 VCF 文件中的联系人姓名转换为拼音，并添加到 NICKNAME 字段"""
        contact_lines = self._read_file()
        updated_contact = []

        for line in contact_lines:
            updated_contact.append(line)

            # 仅处理包含 N: 的姓名行
            if 'N:' in line:
                last_name = self._extract_name_part(line, part='last')
                first_name = self._extract_name_part(line, part='first')

                # 清洗姓和名
                if last_name:
                    last_name = self._clean_name(last_name)
                if first_name:
                    first_name = self._clean_name(first_name)

                # 合并清洗后的姓名（姓在前，名在后）
                full_name = ''
                if last_name:
                    full_name += last_name
                if first_name:
                    full_name += first_name

                # 如果合并后不为空，则转换为拼音并生成 NICKNAME
                if full_name:
                    phonetic_name = self._convert_to_phonetic(full_name)
                    updated_contact.append(f"NICKNAME:{phonetic_name}\n")

        self._write_file(updated_contact)

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
        if part == 'last':
            match = re.findall(r"N:([^;]+);", line)  # 匹配姓
        else:
            match = re.findall(r"N:[^;]*;([^;]+);", line)  # 匹配名

        return match[0] if match else None

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

        # 步骤 1：去除括号及内容（兼容中英文括号、方括号、书名号等）
        name = re.sub(r'[（(【\[].*?[）)】\]]', '', name)

        # 步骤 2：处理连字符
        # 如果存在 '-'，则只取最后一个 '-' 之后的部分。
        # 例如 "张三-备注" -> "备注"；"A-B-张三" -> "张三"
        if '-' in name:
            name = name.split('-')[-1]

        # 去除首尾多余空格
        return name.strip()

    def _convert_to_phonetic(self, name):
        """
        将汉字转换为拼音，并将拼音的每个字母首字母大写

        :param name: 姓或名
        :return: 转换后的拼音字符串
        """
        pinyin_list = self.py_engine.hanzi2pinyin(name)
        return ''.join([item.capitalize() for item in pinyin_list if item])


if __name__ == '__main__':
    filename = 'contacts.vcf'
    generator = PhoneticGenerator(filename)
    generator.convert()
