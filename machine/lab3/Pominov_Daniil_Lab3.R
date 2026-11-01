library(MASS)
library(pROC)
library(caret)
library(ggplot2)
library(vcd)
heart <- read.csv("heart.csv")
# проверка и удаление пропусков
sum(is.na(heart))
heart <- na.omit(heart)
cat_vars <- c("Sex", "ChestPainType", "RestingECG", "ExerciseAngina", "ST_Slope")
heart[cat_vars] <- lapply(heart[cat_vars], as.factor)
heart$HeartDisease <- as.factor(heart$HeartDisease)
summary(heart)
# визуальный анализ связи HeartDisease и ST_Slope
mosaic(~ ST_Slope + HeartDisease, data = heart,
       shade = TRUE,
       legend = TRUE,
       main = "Связь наклона сегмента ST и наличия заболевания")
ggplot(heart, aes(x = ST_Slope, fill = HeartDisease)) +
  geom_bar(position = "fill") +
  labs(y = "Доля", title = "Распределение HeartDisease по ST_Slope") +
  theme_minimal()
# нормировка
num_vars <- c("Age", "RestingBP", "Cholesterol", "MaxHR", "Oldpeak")
heart[num_vars] <- scale(heart[num_vars])
summary(heart[num_vars])
# разделение
train_index <- createDataPartition(heart$HeartDisease, p = 0.7, list = FALSE)
train <- heart[train_index, ]
test  <- heart[-train_index, ]
cat("Размер обучающей выборки:", nrow(train))
cat("Размер контрольной выборки:", nrow(test))
# классификаторы
logit_model <- glm(HeartDisease ~ ., data = train, family = binomial)
summary(logit_model)
lda_model <- lda(HeartDisease ~ ., data = train)
lda_model
# оценки
test$pred_logit <- predict(logit_model, newdata = test, type = "response")
test$class_logit <- factor(ifelse(test$pred_logit > 0.5, "1", "0"),
                           levels = levels(test$HeartDisease))
conf_logit <- table(Predicted = test$class_logit, Actual = test$HeartDisease)
print(conf_logit)
cm_logit <- confusionMatrix(test$class_logit, test$HeartDisease, positive = "1")
cm_logit$byClass[c("Sensitivity", "Specificity", "Precision", "F1")]
cm_logit$overall["Accuracy"]
# ROC
m_ROC_logit.roc <- roc(test$HeartDisease, test$pred_logit)
plot(m_ROC_logit.roc, grid.col = c("green", "red"), grid = c(0.1, 0.2),
     print.auc = TRUE, print.thres = TRUE,
     main = "ROC: логистическая регрессия")
plot(smooth(m_ROC_logit.roc), col = "blue", add = TRUE, print.auc = FALSE)
# LDA
pred_lda        <- predict(lda_model, newdata = test)
test$class_lda  <- pred_lda$class
test$pred_lda   <- pred_lda$posterior[, "1"]
conf_lda <- table(Predicted = test$class_lda, Actual = test$HeartDisease)
print(conf_lda)
cm_lda <- confusionMatrix(test$class_lda, test$HeartDisease, positive = "1")
cm_lda$byClass[c("Sensitivity", "Specificity", "Precision", "F1")]
cm_lda$overall["Accuracy"]
# ROC-анализ
m_ROC_lda.roc <- roc(test$HeartDisease, test$pred_lda)
plot(m_ROC_lda.roc, grid.col = c("green", "red"), grid = c(0.1, 0.2),
     print.auc = TRUE, print.thres = TRUE,
     main = "ROC: LDA")
plot(smooth(m_ROC_lda.roc), col = "blue", add = TRUE, print.auc = FALSE)
# сравнение
metrics <- data.frame(
  Logit = c(cm_logit$overall["Accuracy"],
            cm_logit$byClass["Sensitivity"],
            cm_logit$byClass["Specificity"],
            cm_logit$byClass["Precision"],
            cm_logit$byClass["F1"],
            AUC = as.numeric(auc(m_ROC_logit.roc))),
  LDA = c(cm_lda$overall["Accuracy"],
          cm_lda$byClass["Sensitivity"],
          cm_lda$byClass["Specificity"],
          cm_lda$byClass["Precision"],
          cm_lda$byClass["F1"],
          AUC = as.numeric(auc(m_ROC_lda.roc)))
)
print(metrics)
