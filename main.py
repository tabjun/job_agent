import asyncio
from job_hunter import run_job_hunter
from revise_resume import run_resume_reviser

async def main():
    while True:
        print("\n" + "="*60)
        print(" 🚀 AI 커리어 어시스턴트 통합 메인")
        print("="*60)
        print("1. [Job Hunter] 채용 공고 광범위 검색 및 분석")
        print("2. [Resume Reviser] 맞춤형 자소서/이력서 수정 및 전략 수립")
        print("q. 종료")
        print("-" * 60)
        
        choice = input("원하시는 작업의 번호를 입력하세요: ")
        
        if choice == "1":
            await run_job_hunter()
        elif choice == "2":
            # revise_resume.py를 모듈로 임포트하기 위해 __import__ 또는 미리 import
            from revise_resume import run_resume_reviser
            await run_resume_reviser()
        elif choice.lower() == "q":
            print("프로그램을 종료합니다.")
            break
        else:
            print("잘못된 입력입니다. 다시 선택해주세요.")

if __name__ == "__main__":
    asyncio.run(main())
