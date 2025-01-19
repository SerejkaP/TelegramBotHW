import io
import matplotlib.pyplot as plt


def get_water_visualization(logged_water, water_goal, logged_calories, calorie_goal):
    plt.figure(figsize=(10, 5))
    # График для воды
    plt.subplot(1, 2, 1)
    plt.bar(['Выпито', 'Цель выпить'], [
            logged_water, water_goal], color=['blue', 'green'])
    plt.title('Потребление воды')
    plt.ylabel('Объем (мл)')
    plt.xlabel('Вода')
    plt.ylim(0, max(water_goal, logged_water) + 500)
    # График для калорий
    plt.subplot(1, 2, 2)
    plt.bar(['Потреблено', 'Цель по калориям'], [
            logged_calories, calorie_goal], color=['red', 'green'])
    plt.title('Потребление калорий')
    plt.ylabel('Потребление (калории)')
    plt.xlabel('Калории')
    plt.ylim(0, max(calorie_goal, logged_calories) + 500)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf
