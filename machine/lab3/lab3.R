library(MASS)
library(pROC)
library(ggplot2)

set.seed(123)

df <- read.csv("heart.csv", stringsAsFactors = FALSE)

cat("Размер исходной выборки:", nrow(df), "x", ncol(df), fill = TRUE)
cat("Пропусков до удаления:", sum(is.na(df)), fill = TRUE)
df <- na.omit(df)
cat("Размер после удаления пропусков:", nrow(df), "x", ncol(df), fill = TRUE)

cat_vars <- c("Sex", "ChestPainType", "FastingBS", "RestingECG",
              "ExerciseAngina", "ST_Slope", "HeartDisease")
df[cat_vars] <- lapply(df[cat_vars], factor)
df$HeartDisease <- factor(df$HeartDisease, levels = c(0, 1))

str(df)
p1 <- ggplot(df, aes(x = ST_Slope, fill = HeartDisease)) +
  geom_bar(position = "dodge") +
  labs(title = "Распределение пациентов по наклону сегмента ST",
       x = "ST_Slope", y = "Количество пациентов", fill = "HeartDisease") +
  theme_bw()
ggsave("st_slope_counts.png", p1, width = 7, height = 5, dpi = 150)

p2 <- ggplot(df, aes(x = ST_Slope, fill = HeartDisease)) +
  geom_bar(position = "fill") +
  labs(title = "Доля пациентов с заболеванием в зависимости от ST_Slope",
       x = "ST_Slope", y = "Доля", fill = "HeartDisease") +
  theme_bw()
ggsave("st_slope_proportion.png", p2, width = 7, height = 5, dpi = 150)

cat("Таблица сопряжённости ST_Slope и HeartDisease:", fill = TRUE)
print(table(df$ST_Slope, df$HeartDisease))
cat("Доли HeartDisease = 1 по группам ST_Slope:", fill = TRUE)
print(round(prop.table(table(df$ST_Slope, df$HeartDisease), 1), 3))
numeric_vars <- c("Age", "RestingBP", "Cholesterol", "MaxHR", "Oldpeak")

n_train <- round(0.7 * nrow(df))
train_idx <- sample(seq_len(nrow(df)), n_train)
train <- df[train_idx, ]
test <- df[-train_idx, ]

cat("Обучающая выборка:", nrow(train), "строк; контрольная:", nrow(test), "строк", fill = TRUE)

for (v in numeric_vars) {
  m <- mean(train[[v]])
  s <- sd(train[[v]])
  train[[v]] <- (train[[v]] - m) / s
  test[[v]] <- (test[[v]] - m) / s
}

cat("Средние и стандартные отклонения (обучающая выборка):", fill = TRUE)
print(round(data.frame(
  mean = sapply(df[numeric_vars], mean),
  sd = sapply(df[numeric_vars], sd)
), 3))
logit_model <- glm(HeartDisease ~ ., data = train, family = binomial)
cat("=== Логистическая регрессия ===", fill = TRUE)
print(summary(logit_model))
lda_model <- lda(HeartDisease ~ ., data = train)
cat("=== Линейный дискриминантный анализ ===", fill = TRUE)
print(lda_model)
prob_logit <- predict(logit_model, newdata = test, type = "response")
pred_logit <- factor(ifelse(prob_logit > 0.5, "1", "0"), levels = c("0", "1"))

lda_pred <- predict(lda_model, newdata = test)
pred_lda <- lda_pred$class
prob_lda <- lda_pred$posterior[, "1"]

cat("Матрица ошибок — логистическая регрессия:", fill = TRUE)
cm_logit <- table(Факт = test$HeartDisease, Прогноз = pred_logit)
print(cm_logit)
cat("Матрица ошибок — LDA:", fill = TRUE)
cm_lda <- table(Факт = test$HeartDisease, Прогноз = pred_lda)
print(cm_lda)
metrics <- function(cm) {
  TP <- cm["1", "1"]; TN <- cm["0", "0"]
  FP <- cm["0", "1"]; FN <- cm["1", "0"]
  accuracy <- (TP + TN) / sum(cm)
  sensitivity <- TP / (TP + FN)
  specificity <- TN / (TN + FP)
  precision <- TP / (TP + FP)
  f1 <- 2 * precision * sensitivity / (precision + sensitivity)
  c(accuracy = accuracy, sensitivity = sensitivity, specificity = specificity,
    precision = precision, F1 = f1)
}

res <- rbind(Logistic = metrics(cm_logit), LDA = metrics(cm_lda))
cat("Метрики качества классификации:", fill = TRUE)
print(round(res, 4))
roc_logit <- roc(test$HeartDisease, prob_logit, levels = c("0", "1"),
                 direction = "<", quiet = TRUE)
roc_lda <- roc(test$HeartDisease, prob_lda, levels = c("0", "1"),
               direction = "<", quiet = TRUE)

cat("AUC (лог. регрессия):", round(auc(roc_logit), 4),
    "| 95% ДИ:", paste(round(ci.auc(roc_logit)[c(1, 3)], 4), collapse = " - "), fill = TRUE)
cat("AUC (LDA):", round(auc(roc_lda), 4),
    "| 95% ДИ:", paste(round(ci.auc(roc_lda)[c(1, 3)], 4), collapse = " - "), fill = TRUE)

png("roc_curves.png", width = 1200, height = 900, res = 150)
plot(roc_logit, col = "blue", lwd = 2, main = "ROC-кривые классификаторов",
     print.auc = FALSE)
plot(roc_lda, col = "red", lwd = 2, add = TRUE, print.auc = FALSE)
legend("bottomright",
       legend = c(paste0("Логистическая регрессия, AUC = ", round(auc(roc_logit), 3)),
                  paste0("LDA, AUC = ", round(auc(roc_lda), 3))),
       col = c("blue", "red"), lwd = 2)
dev.off()
