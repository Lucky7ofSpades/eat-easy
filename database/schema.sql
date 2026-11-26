CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS recipes (
    recipe_id UUID PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    servings INTEGER NOT NULL CHECK (servings > 0),
    prep_minutes INTEGER CHECK (prep_minutes >= 0),
    cook_minutes INTEGER CHECK (cook_minutes >= 0),
    cuisine TEXT,
    categories TEXT[],
    instructions TEXT[],

    kcal DOUBLE PRECISION,
    protein DOUBLE PRECISION,
    fat DOUBLE PRECISION,
    carbohydrates DOUBLE PRECISION,
    sugars DOUBLE PRECISION,
    nutrition_complete BOOLEAN,

    url TEXT,

    kcal_per_serving DOUBLE PRECISION,
    protein_per_serving DOUBLE PRECISION,
    fat_per_serving DOUBLE PRECISION,
    carbohydrates_per_serving DOUBLE PRECISION,
    sugars_per_serving DOUBLE PRECISION,

    total_minutes INTEGER CHECK (total_minutes >= 0),
    time_unknown BOOLEAN
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id UUID NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    ingredient_id UUID NOT NULL,
    name_lt TEXT NOT NULL,
    original_name TEXT,
    notes TEXT,
    "group" TEXT,
    quantity DOUBLE PRECISION NOT NULL CHECK (quantity > 0),
    unit TEXT NOT NULL,
    default_unit TEXT,
    grams_per_unit DOUBLE PRECISION CHECK (grams_per_unit > 0),
    total_grams DOUBLE PRECISION CHECK (total_grams > 0),
    conversion_source TEXT,
    source_category TEXT,
    needs_review BOOLEAN,
    quantity_estimated BOOLEAN,

    PRIMARY KEY (recipe_id, position),

    FOREIGN KEY (recipe_id)
        REFERENCES recipes(recipe_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS products (
    store TEXT NOT NULL,
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    brand TEXT,
    price NUMERIC CHECK (price >= 0),
    regular_price NUMERIC CHECK (regular_price >= 0),
    loyalty_card_required BOOLEAN,
    on_promo BOOLEAN,
    unit_price NUMERIC CHECK (unit_price >= 0),
    regular_unit_price NUMERIC CHECK (regular_unit_price >= 0),
    unit TEXT,
    category TEXT,
    category_id TEXT,
    image TEXT,
    url TEXT,
    main_category TEXT,

    PRIMARY KEY (store, id)
);