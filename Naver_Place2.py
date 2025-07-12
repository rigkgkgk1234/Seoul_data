from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import re


def crawl_naver_cafes_by_dong(dong_name, max_count=10):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get('https://map.naver.com/v5')
    time.sleep(5)

    # 검색창 찾기
    search_box = None
    search_selectors = [
        "input.input_search",
        "input[placeholder*='검색']",
        "input[type='text']",
        "#input_search1"
    ]
    for selector in search_selectors:
        try:
            search_box = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            break
        except:
            continue
    if not search_box:
        print("검색창을 찾지 못했습니다.")
        driver.quit()
        return []
    search_box.clear()
    search_box.send_keys(f"{dong_name} 카페")
    search_box.send_keys("\n")
    print(f"'{dong_name} 카페' 검색어 입력 완료")
    time.sleep(8)

    # iframe 전환
    try:
        search_iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
        )
        driver.switch_to.frame(search_iframe)
        print("searchIframe 전환 완료")
    except:
        print("searchIframe을 찾지 못했습니다.")
        driver.quit()
        return []

    # 장소 리스트 찾기
    place_selectors = [
        "li.UEzoS",
        "li.VLTHu",
        "div.place-list-item",
        "li[data-laim-item-id]",
        "div[data-laim-item-id]"
    ]
    used_selector = None
    places = []
    for selector in place_selectors:
        try:
            places = driver.find_elements(By.CSS_SELECTOR, selector)
            if len(places) > 0:
                used_selector = selector
                print(f"장소 리스트 셀렉터: {selector}, 개수: {len(places)}")
                break
        except:
            continue
    if not places:
        print("장소 리스트를 찾지 못했습니다.")
        driver.quit()
        return []

    results = []
    count = 0
    processed_names = set()
    while count < max_count:
        places = driver.find_elements(By.CSS_SELECTOR, used_selector)
        if not places or count >= len(places):
            break
        for idx, place in enumerate(places):
            if count >= max_count:
                break
            try:
                # 이름 추출
                name = ""
                for sel in ["span.TYaxT", "a.place_bluelink", "span.place_name", "div.ps-title"]:
                    try:
                        name_elem = place.find_element(By.CSS_SELECTOR, sel)
                        name = name_elem.text.strip()
                        break
                    except:
                        continue
                if not name or name in processed_names:
                    continue
                # 카드 클릭 (상세페이지 진입)
                clicked = False
                for click_sel in [".header_text_area", ".btn_place_card", "a.place_bluelink"]:
                    try:
                        click_elem = place.find_element(By.CSS_SELECTOR, click_sel)
                        driver.execute_script("arguments[0].scrollIntoView(true);", click_elem)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", click_elem)
                        print(f"[{name}] 상세페이지 클릭 성공 ({click_sel})")
                        time.sleep(3)
                        clicked = True
                        break
                    except Exception as e:
                        print(f"[{name}] 상세페이지 클릭 실패 ({click_sel}): {e}")
                if not clicked:
                    continue
                # entryIframe 또는 메인에서 주소 추출
                addr = ""
                try:
                    entry_iframe = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#entryIframe"))
                    )
                    print(f"[{name}] entryIframe 진입 성공")
                    driver.switch_to.frame(entry_iframe)
                    time.sleep(3)
                    try:
                        # 다양한 주소 선택자 시도
                        addr_selectors = [
                            "span.LDgIH, div.LDgIH",
                            "span.address, div.address",
                            "span[class*='address']",
                            "div[class*='address']",
                            "span[class*='addr']",
                            "div[class*='addr']",
                            "span[class*='location']",
                            "div[class*='location']",
                            "span[class*='place']",
                            "div[class*='place']"
                        ]
                        
                        addr_elems = []
                        for selector in addr_selectors:
                            try:
                                addr_elems = driver.find_elements(By.CSS_SELECTOR, selector)
                                if addr_elems:
                                    print(f"[{name}] 주소 선택자 성공: {selector}")
                                    break
                            except:
                                continue
                        
                        if addr_elems:
                            print(f"[{name}] 주소 후보 개수: {len(addr_elems)}")
                            for elem in addr_elems:
                                print(f"[{name}] 주소 후보: {elem.text}")
                            addr = max((elem.text.strip() for elem in addr_elems), key=len, default="")
                            print(f"[{name}] 주소 최종 선택: {addr}")
                        else:
                            print(f"[{name}] 주소 요소를 찾을 수 없음")
                            addr = ""
                    except Exception as e:
                        print(f"[{name}] 주소 추출 실패(iframe): {e}")
                        addr = ""
                except Exception as e:
                    print(f"[{name}] entryIframe 진입 실패: {e}")
                    # iframe이 없으면 default_content에서 주소 시도
                    try:
                        time.sleep(3)
                        # 다양한 주소 선택자 시도 (메인 페이지)
                        addr_selectors_main = [
                            "span.LDgIH, div.LDgIH",
                            "span.address, div.address",
                            "span[class*='address']",
                            "div[class*='address']",
                            "span[class*='addr']",
                            "div[class*='addr']",
                            "span[class*='location']",
                            "div[class*='location']",
                            "span[class*='place']",
                            "div[class*='place']",
                            "span[class*='info']",
                            "div[class*='info']"
                        ]
                        
                        addr_elems = []
                        for selector in addr_selectors_main:
                            try:
                                addr_elems = driver.find_elements(By.CSS_SELECTOR, selector)
                                if addr_elems:
                                    print(f"[{name}] 주소 선택자 성공(메인): {selector}")
                                    break
                            except:
                                continue
                        
                        if addr_elems:
                            print(f"[{name}] 주소 후보 개수(메인): {len(addr_elems)}")
                            for elem in addr_elems:
                                print(f"[{name}] 주소 후보(메인): {elem.text}")
                            addr = max((elem.text.strip() for elem in addr_elems), key=len, default="")
                            print(f"[{name}] 주소 최종 선택(메인): {addr}")
                        else:
                            print(f"[{name}] 주소 요소를 찾을 수 없음(메인)")
                            addr = ""
                    except Exception as e2:
                        print(f"[{name}] 주소 추출 실패(메인): {e2}")
                        addr = ""
                # 평점, 리뷰수 등은 리스트에서 추출
                driver.switch_to.default_content()
                # searchIframe으로 돌아가기
                try:
                    driver.back()
                    time.sleep(3)
                    search_iframe = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#searchIframe"))
                    )
                    driver.switch_to.frame(search_iframe)
                    time.sleep(1)
                    print(f"[{name}] 리스트로 복귀 완료")
                except Exception as e:
                    print(f"[{name}] 리스트 복귀 실패: {e}")
                    continue
                # 평점
                rating = "0.0"
                for sel in ["span.h69bs.orXYY", "span.rating", "div.ps-rating", "span[class*='rating']"]:
                    try:
                        rating_elems = place.find_elements(By.CSS_SELECTOR, sel)
                        for elem in rating_elems:
                            text = elem.text.strip()
                            m = re.search(r"([0-9]+\.[0-9]+)", text)
                            if m:
                                rating = m.group(1)
                                break
                        if rating != "0.0":
                            break
                    except:
                        continue
                # 리뷰 수
                review = "0"
                for sel in ["span.h69bs", "span.review_count", "div.ps-review", "span[class*='review']"]:
                    try:
                        review_elems = place.find_elements(By.CSS_SELECTOR, sel)
                        for elem in review_elems:
                            text = elem.text.strip()
                            if "리뷰" in text and "별점" not in text:
                                if "+" in text:
                                    review = "999+"
                                else:
                                    nums = re.findall(r'\d+', text)
                                    if nums:
                                        review = nums[0]
                                        break
                        if review != "0":
                            break
                    except:
                        continue
                if review == "0":
                    continue
                results.append({
                    "dong": dong_name,
                    "name": name,
                    "address": addr,
                    "rating": rating,
                    "review_count": review
                })
                processed_names.add(name)
                count += 1
            except Exception as e:
                print(f"[예외] {e}")
                driver.switch_to.default_content()
                continue
        break
    driver.quit()
    return results


if __name__ == "__main__":
    print("\n[네이버 지도 카페 수집기]")
    print("동 이름을 입력하면 카페를 검색, 수집합니다.")
    
    # 동 이름 입력받기
    dong_name = input("\n수집할 지역 이름을 입력하세요(동 단위): ").strip()

    if dong_name.lower() in ["exit", "quit", "q", "종료"]:
        print("프로그램을 종료합니다.")
        exit()

    if not dong_name:
        print("동 단위로 입력해주세요.")
        exit()
    
    # 카페 수 입력받기
    max_count_input = input("수집할 카페 수를 입력하세요: ").strip()
    if not max_count_input.isdigit():
        print("숫자를 입력해주세요.")
        exit()
    max_count = int(max_count_input)

    print(f"\n[{dong_name}] 카페 정보 수집 중...")
    try:
        results = crawl_naver_cafes_by_dong(dong_name, max_count=max_count)
        if results:
            df = pd.DataFrame(results)
            print(f"\n[{dong_name}] 카페 리스트 (총 {len(df)}개):")
            print(df[['name', 'address', 'rating', 'review_count']].to_string(index=False))
            # 파일 저장: dong 컬럼 제외
            save_cols = [col for col in df.columns if col != 'dong']
            filename = f"{dong_name}_카페리스트.csv"
            df[save_cols].to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n파일로 저장 완료: {filename}")
        else:
            print(f"[{dong_name}]에서 카페를 찾지 못했습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
    
    print("\n수집이 완료되었습니다.")


# 예시 코드
'''
if __name__ == "__main__":
    dong_name = "천호동"
    max_count = 10
    print("\n==============================")
    print(f"[네이버 지도 카페 수집기] - '{dong_name}' 예시 실행")
    print("==============================\n")
    print(f"[{dong_name}] 카페 정보 수집 중...")
    results = crawl_naver_cafes_by_dong(dong_name, max_count=max_count)
    if results:
        df = pd.DataFrame(results)
        print("\n========== 결과 ==========")
        print(df[['name', 'address', 'rating', 'review_count']].to_string(index=False))
        print("=========================")
        print(f"총 {len(df)}개 카페를 수집했습니다.")
        # dong 컬럼 제외하고 저장
        save_cols = [col for col in df.columns if col != 'dong']
        filename = f"{dong_name}_카페리스트.csv"
        df[save_cols].to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n파일로 저장 완료: {filename}")
    else:
        print(f"[{dong_name}]에서 카페를 찾지 못했습니다.")
'''