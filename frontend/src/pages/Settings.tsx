import { useState } from 'react'

const tabs = ['프로필', '계정', '알림', '보안', '팀 관리']

export default function Settings() {
  const [activeTab, setActiveTab] = useState('프로필')

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-lg font-bold text-gray-800 dark:text-white">설정</h1>
        <p className="text-xs text-gray-400 mt-1">계정과 팀 설정을 관리하세요</p>
      </div>

      <div className="flex gap-6">
        <div className="w-40 flex-shrink-0">
          <div className="flex flex-col gap-1">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`text-left text-sm px-3 py-2 rounded-lg transition ${
                  activeTab === tab
                    ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium'
                    : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1">
          {activeTab === '프로필' && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-5">프로필 정보</h2>
              <div className="flex items-center gap-4 mb-6">
                <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                  <span className="text-2xl text-blue-600 dark:text-blue-300 font-medium">김</span>
                </div>
                <div>
                  <button className="text-xs text-blue-500 border border-blue-200 dark:border-blue-700 px-3 py-1.5 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/30">
                    사진 변경
                  </button>
                  <p className="text-xs text-gray-400 mt-1">JPG, PNG 최대 5MB</p>
                </div>
              </div>
              <div className="flex flex-col gap-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">이름</label>
                    <input defaultValue="김나연" className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 outline-none focus:border-blue-400" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">직책</label>
                    <input defaultValue="팀 리더" className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 outline-none focus:border-blue-400" />
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">이메일</label>
                  <input defaultValue="nayoung@example.com" className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 outline-none focus:border-blue-400" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">언어</label>
                  <select className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 outline-none focus:border-blue-400">
                    <option>한국어</option>
                    <option>English</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">시간대</label>
                  <select className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 outline-none focus:border-blue-400">
                    <option>UTC+09:00 서울</option>
                    <option>UTC+00:00 런던</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end mt-6">
                <button className="text-xs text-white bg-blue-600 px-4 py-2 rounded-lg hover:bg-blue-700">
                  저장하기
                </button>
              </div>
            </div>
          )}

          {activeTab === '알림' && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-5">알림 설정</h2>
              <div className="flex flex-col gap-4">
                {[
                  { label: '회의 분석 완료 알림', desc: '분석이 완료되면 알림을 받아요' },
                  { label: '업무 마감 알림', desc: '업무 마감 1일 전에 알림을 받아요' },
                  { label: '이메일 초안 생성 알림', desc: '이메일 초안이 생성되면 알림을 받아요' },
                  { label: '팀원 업무 완료 알림', desc: '팀원이 업무를 완료하면 알림을 받아요' },
                ].map((item, i) => (
                  <div key={i} className="flex items-center justify-between py-3 border-b border-gray-50 dark:border-gray-700 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{item.label}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{item.desc}</p>
                    </div>
                    <div className="w-10 h-5 bg-blue-500 rounded-full relative cursor-pointer flex-shrink-0">
                      <div className="w-4 h-4 bg-white rounded-full absolute right-0.5 top-0.5 shadow-sm"></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === '계정' && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-5">계정 설정</h2>
              <div className="flex flex-col gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">현재 비밀번호</label>
                  <input type="password" className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 outline-none focus:border-blue-400" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">새 비밀번호</label>
                  <input type="password" className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 outline-none focus:border-blue-400" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">비밀번호 확인</label>
                  <input type="password" className="w-full text-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 outline-none focus:border-blue-400" />
                </div>
                <div className="flex justify-end mt-2">
                  <button className="text-xs text-white bg-blue-600 px-4 py-2 rounded-lg hover:bg-blue-700">변경하기</button>
                </div>
              </div>
            </div>
          )}

          {(activeTab === '보안' || activeTab === '팀 관리') && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6 flex items-center justify-center h-40">
              <p className="text-sm text-gray-400">준비 중인 기능이에요 😊</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}