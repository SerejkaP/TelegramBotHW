import io
import matplotlib.pyplot as plt


def get_water_visualization(logged_water, water_goal, logged_calories, calorie_goal, logged_activity, activity_goal):
    plt.figure(figsize=(15, 5))
    # Вода
    plt.subplot(1, 3, 1)
    plt.bar(
        ['Выпито', 'Цель выпить'],
        [logged_water, water_goal],
        color=['blue', 'green']
    )
    plt.title('Потребление воды')
    plt.ylabel('Объем (мл)')
    plt.xlabel('Вода')
    plt.ylim(0, max(water_goal, logged_water) + 100)
    # Калории
    plt.subplot(1, 3, 2)
    plt.bar(
        ['Потреблено', 'Цель по калориям'],
        [logged_calories, calorie_goal],
        color=['red', 'green']
    )
    plt.title('Потребление калорий')
    plt.ylabel('Потребление (калории)')
    plt.xlabel('Калории')
    plt.ylim(0, max(calorie_goal, logged_calories) + 100)
    # Активность
    plt.subplot(1, 3, 3)
    plt.bar(
        ['Активность', 'Цель активности'],
        [logged_activity, activity_goal],
        color=['orange', 'green']
    )
    plt.title('Активность за день')
    plt.ylabel('Активность (минуты)')
    plt.xlabel('Активность')
    plt.ylim(0, max(activity_goal, logged_activity) + 10)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf
