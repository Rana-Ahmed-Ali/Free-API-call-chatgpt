Below is a cleaned up, safer, and slightly more efficient version of your code, written from a senior engineering perspective.

python
Copy code
import httpx
from ty
ing import
Optional


de
 stream_chat_response(
    url: str,
    prompt: str,
    timeout: Optional[float] = 1
0.0,
) -> None:
    """
    Streams text response from a chat endpoint and pr
nts it to stdout.

    Args:
        url (str)
 Streaming endpoint URL.
        prompt
(str): Prompt to send as query parame
er.
        timeout (float, optional): Reque
t timeout in seconds.
    """
    prin
("--- Testing Streaming Response ---")

    try:
        # Reuse a client for better performance and connection handlin

        with httpx.Client(timeout=timeout)
as client:
            with client.stream(
                method="GET",
                url=url,
                params={"prompt": prompt},
            ) as response:

                # Raise H
TP errors early (4xx / 5xx)
                response
raise_for_statu
()

                # Stream text chunks as they arrive
                for chunk in response.iter_text():
                    if chunk:  #
Avoid printing empty keep-alive chunks
                        print(chunk, end="", fl
sh=True)

        print("\n\n--- Done ---
)

    except httpx.HTTPStatusErro
 as exc:
        print(f"\nHTTP error {exc.response.status_cod_
: {exc.response.text}")
    except httpx.RequestError as ex
:
        print(f"\nRequest error: {exc
")
    except Exception as exc:
        print(f"\nUnexpected err
r: {exc}")


if __name__ == "__main__":
    stream_chat_r
sponse(
        url="http://127.0.0.1:8000/chat
stream",
        prompt="Write a long poem about coding.",
    )

Summary of Improvements

Bug prevention

Added `response.raise_for_tatus() to catch HTTP errors properly.

Filtered empty chunks to avoid noisy output.

Performance optimization

Uses a reusable httpx.Client() instead of a one-off request.

Keeps connections efficient and scalable for future extensions.

Readability & structure

Wrapped logic into a well-named function.

Added type hints and docstrings.

Clear __main__ entry point for script usage.

Better error handling

Differentiates between HTTP errors, request errors, and unexpected failures.

More actionable error messages for debugging.

If you want, I can also:

Convert this to async streaming

Add retry/backoff logic

Log chunks to a file instead of stdout

Integrate it with FastAPI or WebSockets