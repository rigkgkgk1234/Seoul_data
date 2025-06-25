import pandas as pd

# CSV 경로 설정
url = "https://raw.githubusercontent.com/rigkgkgk1234/Seoul_data/refs/heads/main/Korea_code_20250415.csv"

df = pd.read_csv(url, encoding='utf-8')

# 서울특별시 추출
seoul_df = df[df['시도명'] == '서울특별시'] 

# 앞 4개 컬럼만 저장 - loc 사용, DF 형태 유지
seoul_df = seoul_df.loc[:, ['법정동코드', '시도명', '시군구명', '읍면동명']]

seoul_df.to_csv("data/Seoul_code.csv", index=False, encoding='utf-8-sig')

print(f"총 {len(seoul_df)}개 저장됨") 