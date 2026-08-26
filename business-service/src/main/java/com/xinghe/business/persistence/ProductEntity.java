package com.xinghe.business.persistence;

import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

@TableName("products")
public class ProductEntity {
    @TableId
    private String sku;
    private String name;
    private String category;
    private long priceCents;
    private int stock;
    private long version;

    public String getSku() { return sku; }
    public void setSku(String sku) { this.sku = sku; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }
    public long getPriceCents() { return priceCents; }
    public void setPriceCents(long priceCents) { this.priceCents = priceCents; }
    public int getStock() { return stock; }
    public void setStock(int stock) { this.stock = stock; }
    public long getVersion() { return version; }
    public void setVersion(long version) { this.version = version; }
}
