require(tidyverse)
require(mongolite)

sales_plot <- function(collection){
  #onnect to mongo DB
  connection = mongo(
    collection = paste0(collection,'_sales'),
    db = "mvh",
    url ="mongodb+srv://mvh:W1xIlKbF46rFCsiM@cluster0.ecrau.mongodb.net",
    verbose = FALSE,
    options = ssl_options()
  )
  
  #pull data from mongo
  sales_df = connection$find()%>% 
    #filter for just eth sales
    filter(sale_currency %in% c('ETH','WETH'))%>% 
    mutate(date = as_date(time)) 
  
  sales_summary = sales_df%>% 
    group_by(date) %>% 
    summarise(date_mean = median(sale_price),n_sales= n(),date_volume = sum(sale_price)) %>% 
    mutate(cum_volume = cumsum(date_volume))
  
  p <- ggplot(data = sales_summary, aes(x = date, y = date_mean)) +
    geom_line(color = "#00AFBB", size = 1)+
    stat_smooth(color = "#FC4E07", fill = "#FC4E07",method = "loess")+
    labs(x= 'Date', y='Average price (ETH)') + 
    scale_x_date(date_labels = "%b/%Y")
  
  return(p)

}