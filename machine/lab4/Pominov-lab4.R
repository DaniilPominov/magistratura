library(e1071)
library(ggplot2)

dat <- read.csv("var1.csv", stringsAsFactors = FALSE)
dat$y <- as.factor(dat$y)
str(dat)

# Радиальный SVM
svmfit_radial <- svm(y ~ ., data = dat, kernel = "radial", cost = 100, scale = FALSE)
summary(svmfit_radial)

# Новые точки
testdata <- data.frame(
  x.1 = c(0, -0.3, 2),
  x.2 = c(1, 2.4, 2.1)
)
testdata$ypred <- predict(svmfit_radial, testdata)

cat("Предсказанные классы для новых точек:\n")
print(testdata)

# Сетка для визуализации
grid <- expand.grid(
  x.1 = seq(min(dat$x.1) - 0.1, max(dat$x.1) + 0.1, length.out = 500),
  x.2 = seq(min(dat$x.2) - 0.1, max(dat$x.2) + 0.1, length.out = 500)
)

preds_radial <- predict(svmfit_radial, grid)
df_radial <- data.frame(grid, preds = preds_radial)

support_radial <- rep("no", nrow(dat))
support_radial[svmfit_radial$index] <- "yes"
dat_plot_radial <- cbind(dat, support = support_radial)

cols <- c("-1" = "blue", "0" = "green", "1" = "red")

g_radial <- ggplot(df_radial, aes(x = x.2, y = x.1)) +
  geom_tile(aes(fill = preds), alpha = 0.6) +
  geom_point(data = dat_plot_radial, aes(color = y, shape = support), size = 2) +
  scale_color_manual(values = cols) +
  geom_point(data = testdata, aes(color = ypred), size = 4, shape = 17, stroke = 1.5) +
  labs(
    title = "SVM с радиальным ядром (cost = 100)",
    x = "x.2", y = "x.1",
    color = "Класс", shape = "Опорный вектор", fill = "Предсказание"
  ) +
  theme_minimal()

print(g_radial)
ggsave("Pominov-radial.pdf", plot = g_radial, width = 8, height = 6, device = cairo_pdf)

# Перекрестная проверка: линейное ядро, подбор cost
set.seed(123)
tuned_svm <- tune(
  svm,
  y ~ x.1 + x.2,
  data = dat,
  kernel = "linear",
  ranges = list(cost = c(0.001, 0.01, 0.1, 1, 10, 100)),
  scale = FALSE
)

cat("\nРезультаты перекрестной проверки (ошибки):\n")
print(tuned_svm$performances)

best_model <- tuned_svm$best.model
cat("Параметры оптимальной модели:\n")
summary(best_model)

# Предсказания оптимальной модели для новых точек
testdata$ypred_opt <- predict(best_model, testdata)

preds_opt <- predict(best_model, grid)
df_opt <- data.frame(grid, preds = preds_opt)

support_opt <- rep("no", nrow(dat))
support_opt[best_model$index] <- "yes"
dat_plot_opt <- cbind(dat, support = support_opt)

g_opt <- ggplot(df_opt, aes(x = x.2, y = x.1)) +
  geom_tile(aes(fill = preds), alpha = 0.6) +
  geom_point(data = dat_plot_opt, aes(color = y, shape = support), size = 2) +
  scale_color_manual(values = cols) +
  geom_point(data = testdata, aes(color = ypred_opt), size = 4, shape = 17, stroke = 1.5) +
  labs(
    title = paste("Оптимальный SVM (ядро: linear, cost =", best_model$cost, ")"),
    x = "x.2", y = "x.1",
    color = "Класс", shape = "Опорный вектор", fill = "Предсказание"
  ) +
  theme_minimal()

print(g_opt)
ggsave("Pominov-linear.pdf", plot = g_opt, width = 8, height = 6, device = cairo_pdf)