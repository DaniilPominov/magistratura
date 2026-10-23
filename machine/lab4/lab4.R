# ============================================================
# Лабораторная работа №4. Нечетный вариант (var1.csv)
# Классификация методом опорных векторов (SVM)
# ============================================================

# install.packages(c("e1071", "ggplot2"))
library(e1071)
library(ggplot2)

# ---------- Загрузка данных ----------
dat <- read.csv("var1.csv", stringsAsFactors = FALSE)
dat$y <- as.factor(dat$y)  # метки классов: -1, 0, 1
str(dat)

# ---------- 1. Построение классификатора с радиальным ядром (cost = 100) ----------
svmfit_radial <- svm(y ~ ., data = dat, kernel = "radial", cost = 100, scale = FALSE)
summary(svmfit_radial)

# ---------- 2. Классификация новых точек ----------
testdata <- data.frame(
  x.1 = c(0, -0.3, 2),
  x.2 = c(1, 2.4, 2.1)
)
ypred_radial <- predict(svmfit_radial, testdata)
testdata$ypred <- ypred_radial

cat("Предсказанные классы для новых точек:\n")
print(testdata)

# ---------- 3. Визуализация радиального классификатора ----------
# Область построения графика (с учетом исправления ошибки из методички)
grid <- expand.grid(
  seq(min(dat[, 1] - 0.1), max(dat[, 1] + 0.1), length.out = 500),
  seq(min(dat[, 2] - 0.1), max(dat[, 2] + 0.1), length.out = 500)
)
names(grid) <- names(dat)[1:2]

# Классификация объектов сетки
preds_radial <- predict(svmfit_radial, grid)
df_radial <- data.frame(grid, preds = preds_radial)

# Пометка опорных векторов
dat$support <- "no"
dat$support[svmfit_radial$index] <- "yes"

# Цвета для 3 классов
cols <- c("-1" = "blue", "0" = "green", "1" = "red")

# Построение графика
g_radial <- ggplot(df_radial, aes(x = x.2, y = x.1)) +
  geom_tile(aes(fill = preds), alpha = 0.6) +
  geom_point(data = dat, aes(color = y, shape = support), size = 2) +
  scale_color_manual(values = cols) +
  geom_point(data = testdata, aes(color = ypred), size = 4, shape = 17, stroke = 1.5) +
  labs(
    title = "SVM с радиальным ядром (cost = 100)",
    x = "x.2", y = "x.1",
    color = "Класс", shape = "Опорный вектор", fill = "Предсказание"
  ) +
  theme_minimal()

print(g_radial)
ggsave("Pominov-radial.pdf", plot = g_radial, width = 8, height = 6)

# ---------- 4. Перекрестная проверка (tune) для поиска оптимального ядра ----------
# Фиксируем cost = 10, перебираем 4 типа ядер
set.seed(123)
tuned_svm <- tune(
  svm,
  y ~ .,
  data = dat,
  ranges = list(kernel = c("polynomial", "radial", "linear", "sigmoid")),
  cost = 10
)

# (b) Вывод значений ошибок для каждой модели
cat("\nРезультаты перекрестной проверки (ошибки):\n")
print(tuned_svm$performances)

# Оптимальная модель
best_model <- tuned_svm$best.model
cat("\nПараметры оптимальной модели:\n")
summary(best_model)

# ---------- (c) Визуализация оптимального классификатора ----------
preds_opt <- predict(best_model, grid)
df_opt <- data.frame(grid, preds = preds_opt)

# Пометка опорных векторов для оптимальной модели
dat$support_opt <- "no"
dat$support_opt[best_model$index] <- "yes"

g_opt <- ggplot(df_opt, aes(x = x.2, y = x.1)) +
  geom_tile(aes(fill = preds), alpha = 0.6) +
  geom_point(data = dat, aes(color = y, shape = support_opt), size = 2) +
  scale_color_manual(values = cols) +
  geom_point(data = testdata, aes(color = ypred), size = 4, shape = 17, stroke = 1.5) +
  labs(
    title = paste("Оптимальный SVM (ядро:", best_model$kernel, ", cost = 10)"),
    x = "x.2", y = "x.1",
    color = "Класс", shape = "Опорный вектор", fill = "Предсказание"
  ) +
  theme_minimal()

print(g_opt)
ggsave("Pominov-linear.pdf", plot = g_opt, width = 8, height = 6)
