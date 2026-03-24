from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .services import get_ai_matches
from .models import MatchRequest, MatchResult


def match_view(request):
    """
    Страница /match/ — форма запроса и результаты AI-подбора.
    Доступна всем, но сохраняет историю только для авторизованных.
    """
    results = []
    prompt = ""
    error = None

    if request.method == "POST":
        prompt = request.POST.get("prompt", "").strip()
        if not prompt:
            error = "Пожалуйста, опишите, что вы ищете."
        else:
            matches = get_ai_matches(prompt)

            # Сохраняем запрос для авторизованных
            if request.user.is_authenticated and matches:
                match_req = MatchRequest.objects.create(
                    tourist=request.user,
                    prompt=prompt,
                )
                for m in matches:
                    MatchResult.objects.create(
                        match_request=match_req,
                        guide=m["guide"],
                        score=m["score"],
                        reason=m["reason"],
                        compromise=m["compromise"],
                    )

            results = matches

    return render(request, "matching/match.html", {
        "results": results,
        "prompt": prompt,
        "error": error,
    })
