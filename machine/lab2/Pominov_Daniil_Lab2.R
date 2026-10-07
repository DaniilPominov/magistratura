#lab2 вариант 11
library(psych)
library(ggplot2)
library(vcd)

data <- read.csv("NCbirth.csv", header = TRUE, sep = ",")

# Преобразование в факторные переменные
data$Plural <- factor(data$Plural, levels = c(1, 2, 3))
data$Sex <- factor(data$Sex, levels = c(1, 2), labels = c("male", "female"))
data$Marital <- factor(data$Marital, levels = c(1, 2), labels = c("yes", "no"))
data$RaceMom <- factor(data$RaceMom, levels = 1:8, 
                       labels = c("white", "black", "american indian", "chinese", 
                                  "japanese", "hawaiian", "filipino", "other asian or pacific islander"))
data$HispMom <- factor(data$HispMom, levels = c("C", "M", "N", "O", "P", "S"),
                       labels = c("Cuban", "Mexican", "not Hispanic", "Other Hispanic", 
                                  "Puerto Rico", "Central/South America"))
data$Smoke <- factor(data$Smoke, levels = c(0, 1), labels = c("no", "yes"))
data$Low <- factor(data$Low, levels = c(0, 1), labels = c("no", "yes"))
data$Premie <- factor(data$Premie, levels = c(0, 1), labels = c("no", "yes"))

summary(data)

plot(data$Weeks, data$BirthWeightGm,
     main = "Зависимость веса новорожденного от срока беременности",
     xlab = "Продолжительность беременности (недели)",
     ylab = "Вес новорожденного (г)",
     col = "blue", pch = 20)

subset_data <- data[which(data$RaceMom == "white" & data$Smoke == "yes"), ]

hist(subset_data$BirthWeightGm,
     breaks = 10,
     prob = TRUE,
     main = "Распределение веса (белые, курящие матери)",
     xlab = "Вес новорожденного (г)",
     ylab = "Относительная частота",
     col = "lightgreen")

lines(density(subset_data$BirthWeightGm), col = "red", lwd = 2)

boxplot(BirthWeightGm ~ RaceMom, data = data,
        main = "Распределение веса по расе матери",
        xlab = "Раса матери",
        ylab = "Вес новорожденного (г)",
        las = 2, col = "lightyellow",
        cex.axis = 0.5)

mean_weights <- tapply(data$BirthWeightGm, data$RaceMom, mean, na.rm = TRUE)
barplot(mean_weights,
        main = "Средний вес новорожденных по расе матери",
        xlab = "Раса матери",
        ylab = "Средний вес (г)",
        col = "steelblue", las = 2)

mosaic(~ Sex + Plural + Low, data = data,
       shade = TRUE,
       legend = TRUE,
       main = "Мозаичная диаграмма: Sex, Plural, Low")

pairs.panels(data[, c("Plural", "BirthWeightGm", "Gained")],
             title = "Матрица связей: Plural, BirthWeightGm, Gained")

low_weight <- data[data$Low == "yes", ]
low_weight$ID_ordered <- reorder(low_weight$ID, low_weight$MomAge)
dotchart(low_weight$MomAge,
         groups = low_weight$Smoke,
         gcolor = c("darkgreen", "red"),
         color = ifelse(low_weight$Smoke == "no", "darkgreen", "red"),
         main = "Возраст матерей новорожденных с низким весом",
         xlab = "Возраст матери",
         ylab = "Наблюдения")
legend("bottomright", legend = c("Не курят", "Курят"),
       col = c("darkgreen", "red"), pch = 19)


my_palette <- c(
  "white"                           = "#E69F00", 
  "black"                           = "#56B4E9", 
  "american indian"                 = "#009E73", 
  "chinese"                         = "#F0E442", 
  "japanese"                        = "#0072B2", 
  "hawaiian"                        = "#D55E00",
  "filipino"                        = "#CC79A7",
  "other asian or pacific islander" = "#999999" 
)

ggplot(data, aes(x = MomAge, fill = RaceMom)) +
  geom_area(stat = "bin", bins = 10, position = "stack", alpha = 0.8) +
  scale_fill_manual(values = my_palette, name = "Раса матери") +
  labs(title = "Число новорожденных по возрасту матери и расе",
       x = "Возраст матери",
       y = "Количество новорожденных",
       fill = "Раса матери") +
  theme_minimal()
