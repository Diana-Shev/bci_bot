Write-Host "Запуск теста..." -ForegroundColor Green
python test_simple.py
Write-Host "Тест завершен. Нажмите любую клавишу для продолжения..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
