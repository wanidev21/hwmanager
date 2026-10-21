// Firestore 보안 규칙 테스트 (에뮬레이터 — 실제 DB와 무관)
// 실행: cd tests/rules && npm install && npm test   (Java 필요)
import { test, before, after, beforeEach } from 'node:test';
import { readFileSync } from 'node:fs';
import { initializeTestEnvironment, assertSucceeds, assertFails } from '@firebase/rules-unit-testing';
import { doc, getDoc, setDoc, updateDoc, deleteDoc, addDoc, collection, getDocs, query, where } from 'firebase/firestore';

let env;
const ALLOWED = 'member@example.com';
const ADMIN = 'admin@example.com';

// 로그인 상태별 DB 핸들
const member   = () => env.authenticatedContext('u-member',   { email: ALLOWED, email_verified: true }).firestore();
const member2  = () => env.authenticatedContext('u-member2',  { email: 'member2@example.com', email_verified: true }).firestore();
const admin    = () => env.authenticatedContext('u-admin',    { email: ADMIN, email_verified: true }).firestore();
const stranger = () => env.authenticatedContext('u-stranger', { email: 'stranger@example.com', email_verified: true }).firestore();
const unverified = () => env.authenticatedContext('u-unv',    { email: ALLOWED, email_verified: false }).firestore();
const anon     = () => env.unauthenticatedContext().firestore();

before(async () => {
  env = await initializeTestEnvironment({
    projectId: 'demo-hwmanager',
    firestore: { rules: readFileSync(new URL('../../firestore.rules', import.meta.url), 'utf8') },
  });
});
after(async () => { await env?.cleanup(); });

// 매 테스트: 허용 목록·사용자·샘플 문서 (규칙 우회로 직접 넣음)
beforeEach(async () => {
  await env.clearFirestore();
  await env.withSecurityRulesDisabled(async ctx => {
    const db = ctx.firestore();
    await setDoc(doc(db, 'config/access'), { emails: [ALLOWED, 'member2@example.com', ADMIN] });
    await setDoc(doc(db, 'users/u-member'), { role: 'user', displayName: 'M' });
    await setDoc(doc(db, 'users/u-admin'), { role: 'admin', displayName: 'A' });
    await setDoc(doc(db, 'tickets/t1'), { title: '장애' });
    await setDoc(doc(db, 'tickets/t1/logs/l1'), { text: '기록', by: 'u-member' });
    await setDoc(doc(db, 'kb_articles/k1'), { title: '내 KB', user_id: 'u-member' });
    await setDoc(doc(db, 'audit_logs/a1'), { action: '등록', by: 'u-member' });
    await setDoc(doc(db, 'parts/p1'), { name: 'GPU', status: '요청' });
  });
});

// ── 접근 자격 ──
test('비로그인·허용 목록 밖·이메일 미인증 계정은 공용 데이터 읽기 불가', async () => {
  for (const db of [anon(), stranger(), unverified()]) {
    await assertFails(getDoc(doc(db, 'tickets/t1')));
    await assertFails(getDoc(doc(db, 'config/access')));
    await assertFails(setDoc(doc(db, 'customers/c1'), { name: 'x' }));
  }
});

test('허용 계정은 공용 업무 데이터 읽기·쓰기 가능 (부품·작업 포함)', async () => {
  const db = member();
  await assertSucceeds(getDoc(doc(db, 'tickets/t1')));
  for (const col of ['customers', 'projects', 'assets', 'tickets', 'jobs', 'parts', 'job_templates', 'delivery_notes', 'delivery_items']) {
    await assertSucceeds(setDoc(doc(db, `${col}/new1`), { name: 'x' }));
    await assertSucceeds(updateDoc(doc(db, `${col}/new1`), { name: 'y' }));
    await assertSucceeds(deleteDoc(doc(db, `${col}/new1`)));
  }
});

test('목록에 없는 컬렉션은 허용 계정도 차단', async () => {
  await assertFails(setDoc(doc(member(), 'secrets/s1'), { x: 1 }));
  await assertFails(getDoc(doc(admin(), 'secrets/s1')));
});

// ── 허용 목록·관리자 ──
test('허용 목록은 관리자만 수정', async () => {
  await assertSucceeds(getDoc(doc(member(), 'config/access')));
  await assertFails(updateDoc(doc(member(), 'config/access'), { emails: [ALLOWED, 'evil@example.com'] }));
  await assertSucceeds(updateDoc(doc(admin(), 'config/access'), { emails: [ALLOWED, ADMIN] }));
});

test('사용자 문서: 본인 생성은 role=user만, 본인 role 변경 불가, 관리자는 변경 가능', async () => {
  await assertFails(setDoc(doc(member2(), 'users/u-member2'), { role: 'admin' }));
  await assertSucceeds(setDoc(doc(member2(), 'users/u-member2'), { role: 'user' }));
  await assertFails(setDoc(doc(member2(), 'users/u-member'), { role: 'user' }));            // 남의 문서 생성
  await assertFails(updateDoc(doc(member(), 'users/u-member'), { role: 'admin' }));          // 셀프 승격
  await assertSucceeds(updateDoc(doc(member(), 'users/u-member'), { displayName: '새 이름' }));
  await assertFails(updateDoc(doc(member2(), 'users/u-member'), { displayName: '남이 바꿈' }));
  await assertFails(deleteDoc(doc(member(), 'users/u-admin')));
  await assertSucceeds(updateDoc(doc(admin(), 'users/u-member'), { role: 'admin' }));   // (이 뒤로 u-member는 관리자)
});

// ── 개인 데이터 ──
test('개인 데이터(KB 등)는 본인만 읽기·수정, 남의 이름으로 생성·소유자 바꾸기 불가', async () => {
  await assertSucceeds(getDoc(doc(member(), 'kb_articles/k1')));
  await assertFails(getDoc(doc(member2(), 'kb_articles/k1')));
  await assertFails(updateDoc(doc(member2(), 'kb_articles/k1'), { title: 'x' }));
  await assertFails(deleteDoc(doc(member2(), 'kb_articles/k1')));
  await assertFails(updateDoc(doc(member(), 'kb_articles/k1'), { user_id: 'u-member2' }));   // 소유자 넘기기
  await assertFails(addDoc(collection(member2(), 'kb_articles'), { title: 'x', user_id: 'u-member' }));
  await assertSucceeds(addDoc(collection(member2(), 'calendar_events'), { title: 'x', user_id: 'u-member2' }));
  // 목록 조회는 본인 것 조건이 있어야 함 (조건 없이 전체 조회 차단)
  await assertSucceeds(getDocs(query(collection(member(), 'kb_articles'), where('user_id', '==', 'u-member'))));
  await assertFails(getDocs(collection(member(), 'kb_articles')));
});

// ── 진행 기록·변경 이력 ──
test('티켓 진행 기록: 본인 이름으로만 작성·수정, 삭제는 팀 모두', async () => {
  await assertFails(addDoc(collection(member2(), 'tickets/t1/logs'), { text: 'x', by: 'u-member' }));
  await assertSucceeds(addDoc(collection(member2(), 'tickets/t1/logs'), { text: 'x', by: 'u-member2' }));
  await assertFails(updateDoc(doc(member2(), 'tickets/t1/logs/l1'), { text: '고침' }));
  await assertSucceeds(updateDoc(doc(member(), 'tickets/t1/logs/l1'), { text: '고침' }));
  await assertFails(updateDoc(doc(member(), 'tickets/t1/logs/l1'), { by: 'u-member2' }));
  await assertSucceeds(deleteDoc(doc(member2(), 'tickets/t1/logs/l1')));
});

test('변경 이력: 본인 이름으로 추가만, 수정·삭제는 관리자도 불가', async () => {
  await assertSucceeds(addDoc(collection(member(), 'audit_logs'), { action: '수정', by: 'u-member' }));
  await assertFails(addDoc(collection(member(), 'audit_logs'), { action: '수정', by: 'u-member2' }));
  await assertFails(updateDoc(doc(member(), 'audit_logs/a1'), { action: '삭제' }));
  await assertFails(deleteDoc(doc(admin(), 'audit_logs/a1')));
});
