import os
import argparse

TARGET_CONTROL_TABLE_ITEMS = [
    "Operating Mode",
    "Torque Enable",
    "Min Position Limit",
    "Max Position Limit",
    "Profile Acceleration",
    "Profile Velocity",
    "Goal Position",
    "Present Velocity",
    "Present Position"
]

class DynamixelModelParser:
    def __init__(self, path="./"):
        self.path = path
        self.control_table = {}

    def parse_file(self):

        file_path = self.path

        if not os.path.exists(file_path):
            print(f"[Error] File not found: {file_path}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                is_control_table_section = False
                for line in f:
                    line = line.strip()
                    if not line: continue

                    # [control table] 섹션 시작 감지
                    if line == "[control table]":
                        is_control_table_section = True
                        try:
                            next(f) # 헤더 행(Address	Size	Data Name) 건너뛰기
                        except StopIteration:
                            break
                        continue
                    
                    # 다른 섹션이 시작되면 종료
                    if is_control_table_section and line.startswith('['):
                        break

                    # 데이터 파싱
                    if is_control_table_section:
                        tokens = line.split('\t')
                        if len(tokens) >= 3:
                            addr = int(tokens[0])
                            size = int(tokens[1])
                            name = tokens[2]
                            # 아이템 이름을 키로 하여 주소와 크기만 저장
                            self.control_table[name] = {
                                "address": addr,
                                "size": size
                            }
            
            return self.control_table
            
        except Exception as e:
            print(f"[Error] Failed to parse: {e}")
            return None

if __name__ == "__main__":
    
    parser_arg = argparse.ArgumentParser()
    parser_arg.add_argument("--model", type=str, default="xm540_w270")
    args = parser_arg.parse_args()

    dxl_parser = DynamixelModelParser(path=f"./control_tables/{args.model}.model")
    
    # 제어 테이블 객체 반환받기
    control_config = dxl_parser.parse_file()

    if control_config:

        print(f"\n[Success] Loaded Control Table from: {args.model}.model")
        
        # 요청하신 주요 항목들 출력 테스트
        target_items = TARGET_CONTROL_TABLE_ITEMS

        print(f"{'-'*45}")
        print(f"{'Data Name':<25} | {'Addr':<5} | {'Size'}")
        print(f"{'-'*45}")

        for item in target_items:
            # .get()을 사용하여 안전하게 접근
            info = control_config.get(item)
            if info:
                print(f"{item:<25} | {info.get('address'):<5} | {info.get('size')} byte")
            else:
                print(f"{item:<25} | [Not Found]")

        print(f"{'-'*45}")

    else:
        print(f"[Error] Failed to load control table for model: {args.model}")