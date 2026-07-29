# Aiuto — 트러블슈팅

> STEP이 진행되며 겪은 실제 문제와 해결 과정을 기록한다.
> README의 "설계 결정"이 왜(why) 그렇게 만들었는지를 다룬다면,
> 여기는 실제로 무엇이 깨졌고 어떻게 찾아서 고쳤는지(how)를 다룬다.

---

## 포괄적 예외 처리가 서로 다른 버그 두 개를 숨긴 사례

**태그**: `#예외처리` `#JWT` `#디버깅방법론`

### 문제 상황

JWT 인증 로직(`get_current_user`)을 동기(SQLite) 방식에서 비동기(PostgreSQL)
방식으로 전환하는 과정에서, 아래와 같은 코드를 작성했다.

```python
try:
    payload = jwt.decode(token)          # (1)
    ...
except Exception:                        # (2)
    raise credentials_exception
```

서버를 켜고 로그인 후 보호된 엔드포인트를 호출하면, 항상 `401 인증 정보가
올바르지 않습니다`만 반환됐다. 겉보기엔 "그럴듯하게 동작하는" 상태였다 —
인증되지 않은 요청은 실제로 401을 받았기 때문이다.

### 원인 분석

`except Exception:`으로 모든 예외를 뭉뚱그려 처리하고 있었기 때문에,
**실제로는 코드 자체에 있던 두 가지 버그가 정상적인 "인증 실패"로 위장되고
있었다.**

실행해서 직접 확인한 결과:

```python
>>> setting.SECRET_KEY
AttributeError: 'Settings' object has no attribute 'SECRET_KEY'
```

`config.py`의 `Settings` 필드는 전부 소문자(`secret_key`)로 선언돼 있었는데,
호출부에서는 대문자(`SECRET_KEY`)로 접근하고 있었다. 여기서 `AttributeError`가
발생했지만, `except Exception:`이 이를 그대로 삼켜버려 "토큰이 잘못됐다"는
401로 둔갑했다.

또한 별도로 아래 문제도 같은 방식으로 숨겨져 있었다.

```python
>>> jwt.decode(token)
DecodeError: It is required that you pass in a value for the "algorithms"
argument when calling decode().
```

`jwt.decode()`를 키(key)와 알고리즘(algorithms) 없이 호출하고 있어서 이 역시
매번 예외를 발생시키고 있었다. 즉 **로직이 처음부터 한 번도 정상 동작한 적이
없었는데도, 예외 처리가 이를 "정상적인 인증 실패"처럼 보이게 만들어 문제를
알아챌 방법이 없었다.**

### 해결

1. `except Exception:`을 실제로 예상 가능한 예외 타입으로 좁혔다.
   ```python
   except (jwt.PyJWTError, ValueError):
       raise credentials_exception
   ```
   이렇게 하면 예상 못 한 버그(`AttributeError` 등)는 그대로 드러나고,
   예상되는 인증 실패(토큰 만료·위조, UUID 파싱 실패)만 401로 처리된다.

2. 위 설정값 참조 오류와 `jwt.decode()` 인자 누락을 각각 수정하고,
   토큰 발급/해독 로직을 `security.py`의 `decode_token()` 함수 하나로
   모아 책임을 명확히 했다.

3. 수정 후 정상 토큰, 위조 토큰, 만료 토큰, 잘못된 UUID 형식 등 각 케이스를
   실제로 실행해 예외가 의도한 대로만 잡히는지 검증했다.

### 결과 / 배운 점

- **넓은 `except`는 버그를 고치는 게 아니라 숨긴다.** 코드가 "그럴듯하게
  동작하는 것처럼 보인다"는 것과 "실제로 의도대로 동작한다"는 것은 다르다.
- 예외 처리 범위는 항상 **"내가 실제로 예상하는 실패 케이스가 무엇인가"**를
  먼저 정의하고, 그 타입만 좁혀서 잡아야 한다. `Exception`으로 시작해서
  나중에 좁히는 습관은 이번처럼 진짜 버그를 몇 단계나 늦게 발견하게 만든다.
- 이후 STEP부터는 예외 처리를 작성할 때마다 "지금 이 except가 예상 못 한
  버그까지 같이 삼키고 있지는 않은가"를 항상 확인하는 습관을 들였다.

---
