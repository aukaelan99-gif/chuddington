from pathlib import Path
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from models import Base, ExerciseCatalog, ExerciseType, MuscleGroup, FoodItem

DATABASE_URL = f"sqlite+aiosqlite:///{Path(__file__).parent / 'studywell.db'}"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # legacy column migrations
        cols = await conn.execute(text("PRAGMA table_info(workout_exercises)"))
        names = {row[1] for row in cols.fetchall()}
        if "muscle_group" not in names:
            await conn.execute(
                text("ALTER TABLE workout_exercises ADD COLUMN muscle_group VARCHAR(20) DEFAULT 'other'")
            )

        workout_cols = await conn.execute(text("PRAGMA table_info(workouts)"))
        workout_names = {row[1] for row in workout_cols.fetchall()}
        if "duration_minutes" not in workout_names:
            await conn.execute(text("ALTER TABLE workouts ADD COLUMN duration_minutes REAL"))

        set_cols = await conn.execute(text("PRAGMA table_info(workout_sets)"))
        set_names = {row[1] for row in set_cols.fetchall()}
        if "distance_km" not in set_names:
            await conn.execute(text("ALTER TABLE workout_sets ADD COLUMN distance_km REAL"))

        user_cols = await conn.execute(text("PRAGMA table_info(users)"))
        user_names = {row[1] for row in user_cols.fetchall()}
        if "chulk_avatar_file" not in user_names:
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN chulk_avatar_file VARCHAR(120) DEFAULT 'chulk-default.svg'")
            )
        await conn.execute(
            text(
                "UPDATE users "
                "SET chulk_avatar_file = 'chulk-default.svg' "
                "WHERE chulk_avatar_file IS NULL OR TRIM(chulk_avatar_file) = ''"
            )
        )

        # user_id migrations for all data tables
        for table, col_type in [
            ("study_sessions", "VARCHAR"),
            ("exercise_entries", "VARCHAR"),
            ("meal_entries", "VARCHAR"),
            ("water_logs", "VARCHAR"),
            ("workouts", "VARCHAR"),
            ("daily_goals", "VARCHAR"),
        ]:
            t_cols = await conn.execute(text(f"PRAGMA table_info({table})"))
            t_names = {row[1] for row in t_cols.fetchall()}
            if "user_id" not in t_names:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id {col_type}"))

        # daily_goals: migrate from integer id=1 singleton — if id column is INTEGER type, recreate as VARCHAR
        dg_info = await conn.execute(text("PRAGMA table_info(daily_goals)"))
        dg_cols = {row[1]: row[2] for row in dg_info.fetchall()}
        if dg_cols.get("id", "").upper().startswith("INT"):
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_goals_new (
                    id VARCHAR PRIMARY KEY,
                    user_id VARCHAR,
                    study_minutes INTEGER DEFAULT 120,
                    calorie_target INTEGER DEFAULT 2000,
                    protein_target INTEGER DEFAULT 150,
                    carbs_target INTEGER DEFAULT 250,
                    fat_target INTEGER DEFAULT 70,
                    exercise_minutes INTEGER DEFAULT 30,
                    water_glasses INTEGER DEFAULT 8
                )
            """))
            await conn.execute(text("""
                INSERT OR IGNORE INTO daily_goals_new (id, user_id, study_minutes, calorie_target, protein_target, carbs_target, fat_target, exercise_minutes, water_glasses)
                SELECT CAST(id AS VARCHAR), user_id, study_minutes, calorie_target, 150, 250, 70, exercise_minutes, water_glasses
                FROM daily_goals
            """))
            await conn.execute(text("DROP TABLE daily_goals"))
            await conn.execute(text("ALTER TABLE daily_goals_new RENAME TO daily_goals"))

        # daily_goals macro target columns
        dg_info_after = await conn.execute(text("PRAGMA table_info(daily_goals)"))
        dg_names_after = {row[1] for row in dg_info_after.fetchall()}
        if "protein_target" not in dg_names_after:
            await conn.execute(text("ALTER TABLE daily_goals ADD COLUMN protein_target INTEGER DEFAULT 150"))
        if "carbs_target" not in dg_names_after:
            await conn.execute(text("ALTER TABLE daily_goals ADD COLUMN carbs_target INTEGER DEFAULT 250"))
        if "fat_target" not in dg_names_after:
            await conn.execute(text("ALTER TABLE daily_goals ADD COLUMN fat_target INTEGER DEFAULT 70"))
        if "vitamin_a_target_mcg" not in dg_names_after:
            await conn.execute(text("ALTER TABLE daily_goals ADD COLUMN vitamin_a_target_mcg INTEGER DEFAULT 900"))
        if "vitamin_c_target_mg" not in dg_names_after:
            await conn.execute(text("ALTER TABLE daily_goals ADD COLUMN vitamin_c_target_mg INTEGER DEFAULT 90"))
        if "vitamin_d_target_mcg" not in dg_names_after:
            await conn.execute(text("ALTER TABLE daily_goals ADD COLUMN vitamin_d_target_mcg REAL DEFAULT 15.0"))
        if "vitamin_b12_target_mcg" not in dg_names_after:
            await conn.execute(text("ALTER TABLE daily_goals ADD COLUMN vitamin_b12_target_mcg REAL DEFAULT 2.4"))
        if "calcium_target_mg" not in dg_names_after:
            await conn.execute(text("ALTER TABLE daily_goals ADD COLUMN calcium_target_mg INTEGER DEFAULT 1000"))
        if "iron_target_mg" not in dg_names_after:
            await conn.execute(text("ALTER TABLE daily_goals ADD COLUMN iron_target_mg REAL DEFAULT 18.0"))
        if "potassium_target_mg" not in dg_names_after:
            await conn.execute(text("ALTER TABLE daily_goals ADD COLUMN potassium_target_mg INTEGER DEFAULT 3500"))

        # food_items category column
        fi_info = await conn.execute(text("PRAGMA table_info(food_items)"))
        fi_cols = {row[1] for row in fi_info.fetchall()}
        if "category" not in fi_cols:
            await conn.execute(text("ALTER TABLE food_items ADD COLUMN category VARCHAR DEFAULT 'other'"))
        if "base_grams" not in fi_cols:
            await conn.execute(text("ALTER TABLE food_items ADD COLUMN base_grams REAL DEFAULT 100"))
        if "vitamin_a_mcg" not in fi_cols:
            await conn.execute(text("ALTER TABLE food_items ADD COLUMN vitamin_a_mcg REAL DEFAULT 0"))
        if "vitamin_c_mg" not in fi_cols:
            await conn.execute(text("ALTER TABLE food_items ADD COLUMN vitamin_c_mg REAL DEFAULT 0"))
        if "vitamin_d_mcg" not in fi_cols:
            await conn.execute(text("ALTER TABLE food_items ADD COLUMN vitamin_d_mcg REAL DEFAULT 0"))
        if "vitamin_b12_mcg" not in fi_cols:
            await conn.execute(text("ALTER TABLE food_items ADD COLUMN vitamin_b12_mcg REAL DEFAULT 0"))
        if "calcium_mg" not in fi_cols:
            await conn.execute(text("ALTER TABLE food_items ADD COLUMN calcium_mg REAL DEFAULT 0"))
        if "iron_mg" not in fi_cols:
            await conn.execute(text("ALTER TABLE food_items ADD COLUMN iron_mg REAL DEFAULT 0"))
        if "potassium_mg" not in fi_cols:
            await conn.execute(text("ALTER TABLE food_items ADD COLUMN potassium_mg REAL DEFAULT 0"))
        await conn.execute(
            text(
                "UPDATE food_items "
                "SET vitamin_a_mcg = COALESCE(vitamin_a_mcg, 0), "
                "vitamin_c_mg = COALESCE(vitamin_c_mg, 0), "
                "vitamin_d_mcg = COALESCE(vitamin_d_mcg, 0), "
                "vitamin_b12_mcg = COALESCE(vitamin_b12_mcg, 0), "
                "calcium_mg = COALESCE(calcium_mg, 0), "
                "iron_mg = COALESCE(iron_mg, 0), "
                "potassium_mg = COALESCE(potassium_mg, 0)"
            )
        )

        me_info = await conn.execute(text("PRAGMA table_info(meal_entries)"))
        me_cols = {row[1] for row in me_info.fetchall()}
        if "vitamin_a_mcg" not in me_cols:
            await conn.execute(text("ALTER TABLE meal_entries ADD COLUMN vitamin_a_mcg REAL DEFAULT 0"))
        if "vitamin_c_mg" not in me_cols:
            await conn.execute(text("ALTER TABLE meal_entries ADD COLUMN vitamin_c_mg REAL DEFAULT 0"))
        if "vitamin_d_mcg" not in me_cols:
            await conn.execute(text("ALTER TABLE meal_entries ADD COLUMN vitamin_d_mcg REAL DEFAULT 0"))
        if "vitamin_b12_mcg" not in me_cols:
            await conn.execute(text("ALTER TABLE meal_entries ADD COLUMN vitamin_b12_mcg REAL DEFAULT 0"))
        if "calcium_mg" not in me_cols:
            await conn.execute(text("ALTER TABLE meal_entries ADD COLUMN calcium_mg REAL DEFAULT 0"))
        if "iron_mg" not in me_cols:
            await conn.execute(text("ALTER TABLE meal_entries ADD COLUMN iron_mg REAL DEFAULT 0"))
        if "potassium_mg" not in me_cols:
            await conn.execute(text("ALTER TABLE meal_entries ADD COLUMN potassium_mg REAL DEFAULT 0"))

    await seed_exercise_catalog()
    await seed_food_catalog()


async def seed_food_catalog() -> None:
    # (name, category, base_grams, calories, protein_g, carbs_g, fat_g)
    foods = [
        # Protein
        ("Chicken Breast",      "protein", 100, 165, 31.0,  0.0,  3.6),
        ("Egg",                 "protein",  50,  72,  6.0,  0.4,  5.0),
        ("Ground Beef 85/15",   "protein", 100, 215, 26.0,  0.0, 11.0),
        ("Salmon",              "protein", 100, 208, 20.0,  0.0, 13.0),
        ("Tuna (canned)",       "protein", 100, 109, 24.0,  0.0,  1.0),
        ("Greek Yogurt",        "protein", 100,  65, 11.0,  4.5,  0.35),
        ("Cottage Cheese",      "protein", 100,  98, 11.0,  3.4,  4.3),
        ("Protein Shake",       "protein",  30, 120, 25.0,  3.0,  2.0),
        ("Turkey Breast",       "protein", 100, 135, 30.0,  0.0,  1.0),
        ("Shrimp",              "protein", 100,  99, 24.0,  0.0,  0.3),
        ("Tofu (firm)",         "protein", 100,  76,  8.0,  2.0,  4.0),
        ("Lentils (cooked)",    "protein", 100, 116,  9.0, 20.0,  0.4),
        ("Black Beans (cooked)","protein", 100, 132,  8.9, 24.0,  0.5),
        ("Protein Bar",         "protein",  60, 230, 20.0, 25.0,  7.0),
        ("Pork Loin",           "protein", 100, 173, 27.0,  0.0,  7.0),
        ("Cod",                 "protein", 100, 105, 23.0,  0.0,  1.0),
        ("Tempeh",              "protein", 100, 193, 20.0,  9.0, 11.0),
        ("Edamame",             "protein", 100, 121, 11.0,  9.0,  5.0),
        ("Seitan",              "protein", 100, 143, 25.0,  4.0,  2.0),
        ("Egg White",           "protein",  33,  17,  3.6,  0.2,  0.0),
        ("Ground Turkey",       "protein", 100, 150, 22.0,  0.0,  7.0),
        ("Tilapia",             "protein", 100, 128, 26.0,  0.0,  2.7),
        ("Skyr",                "protein", 100,  60, 11.0,  4.0,  0.2),
        ("Whey Protein",        "protein",  30, 110, 24.0,  2.0,  1.0),
        ("Tofu (silken)",       "protein", 100,  55,  5.0,  2.0,  3.0),
        ("Chickpeas (cooked)",  "protein", 100, 164,  8.9, 27.0,  2.6),
        ("Kidney Beans (cooked)","protein",100, 127,  8.7, 22.8,  0.5),
        ("Jerky",               "protein",  28, 116, 11.0,  3.0,  7.0),
        ("Mahi Mahi",           "protein", 100, 134, 24.0,  0.0,  4.0),
        ("Chicken Thigh",       "protein", 100, 209, 26.0,  0.0, 10.9),
        ("Bison",               "protein", 100, 146, 21.0,  0.0,  6.0),
        ("Venison",             "protein", 100, 158, 30.0,  0.0,  3.2),
        # Grain
        ("White Rice (cooked)", "grain",   100, 130,  2.7, 28.0,  0.3),
        ("Brown Rice (cooked)", "grain",   100, 112,  2.6, 23.0,  0.9),
        ("Oats (dry)",          "grain",   100, 389, 17.0, 66.0,  7.0),
        ("Instant Oats",        "grain",   100, 375, 13.0, 67.0,  7.0),
        ("White Bread",         "grain",    30,  79,  2.7, 15.0,  1.0),
        ("Whole Wheat Bread",   "grain",    30,  81,  4.0, 13.8,  1.1),
        ("Sourdough Bread",     "grain",    30,  80,  3.0, 15.0,  0.8),
        ("Pasta (cooked)",      "grain",   100, 131,  5.0, 25.0,  1.1),
        ("Whole Wheat Pasta",   "grain",   100, 124,  5.0, 26.0,  0.9),
        ("Sweet Potato",        "grain",   100,  86,  1.6, 20.0,  0.1),
        ("Potato",              "grain",   100,  77,  2.0, 17.0,  0.1),
        ("Quinoa (cooked)",     "grain",   100, 120,  4.4, 21.0,  1.9),
        ("Bagel",               "grain",    95, 270, 11.0, 53.0,  1.5),
        ("Tortilla (flour)",    "grain",    49, 146,  3.8, 25.0,  3.5),
        ("Tortilla (corn)",     "grain",    30,  60,  1.5, 12.0,  0.7),
        ("Couscous (cooked)",   "grain",   100, 112,  3.8, 23.0,  0.2),
        ("Barley (cooked)",     "grain",   100, 123,  2.3, 28.0,  0.4),
        ("Rice Noodles (cooked)","grain",  100, 109,  1.8, 24.0,  0.2),
        ("Ramen Noodles (cooked)","grain", 100, 135,  4.0, 25.0,  3.0),
        ("Corn (cooked)",       "grain",   100,  96,  3.4, 21.0,  1.5),
        ("Granola",             "grain",   100, 471, 10.0, 64.0, 20.0),
        ("Cereal (corn flakes)","grain",   100, 357,  7.0, 84.0,  0.4),
        ("Bulgur",              "grain",   100,  83,  3.1, 18.6,  0.2),
        # Fruit
        ("Banana",              "fruit",   118, 105,  1.3, 27.0,  0.4),
        ("Apple",               "fruit",   182,  95,  0.5, 25.0,  0.3),
        ("Green Apple",         "fruit",   182,  95,  0.5, 25.0,  0.3),
        ("Orange",              "fruit",   131,  62,  1.2, 15.0,  0.2),
        ("Mandarin",            "fruit",    88,  47,  0.7, 12.0,  0.3),
        ("Blueberries",         "fruit",   100,  57,  0.7, 14.0,  0.3),
        ("Strawberries",        "fruit",   100,  32,  0.7,  7.7,  0.3),
        ("Mango",               "fruit",   100,  60,  0.8, 15.0,  0.4),
        ("Peach",               "fruit",   150,  59,  1.4, 14.0,  0.4),
        ("Grapes",              "fruit",   100,  69,  0.7, 18.0,  0.2),
        ("Pomegranate",         "fruit",   100,  83,  1.7, 19.0,  1.2),
        ("Pineapple",           "fruit",   100,  50,  0.5, 13.0,  0.1),
        ("Kiwi",                "fruit",   100,  61,  1.1, 15.0,  0.5),
        ("Pear",                "fruit",   178, 101,  0.6, 27.0,  0.2),
        ("Watermelon",          "fruit",   100,  30,  0.6,  7.6,  0.2),
        ("Raspberries",         "fruit",   100,  52,  1.2, 12.0,  0.7),
        ("Blackberries",        "fruit",   100,  43,  1.4, 10.0,  0.5),
        ("Cantaloupe",          "fruit",   100,  34,  0.8,  8.2,  0.2),
        ("Cherry",              "fruit",   100,  63,  1.1, 16.0,  0.2),
        # Vegetable
        ("Broccoli",            "vegetable",100,  34,  2.8,  7.0,  0.4),
        ("Spinach",             "vegetable",100,  23,  2.9,  3.6,  0.4),
        ("Spring Mix",          "vegetable",100,  15,  1.5,  2.0,  0.2),
        ("Avocado",             "vegetable",100, 160,  2.0,  8.5, 14.7),
        ("Carrot",              "vegetable",100,  41,  0.9, 10.0,  0.2),
        ("Cucumber",            "vegetable",100,  15,  0.7,  3.6,  0.1),
        ("Bell Pepper",         "vegetable",100,  31,  1.0,  6.0,  0.3),
        ("Tomato",              "vegetable",100,  18,  0.9,  3.9,  0.2),
        ("Cherry Tomatoes",     "vegetable",100,  18,  0.9,  3.9,  0.2),
        ("Onion",               "vegetable",100,  40,  1.1,  9.3,  0.1),
        ("Garlic",              "vegetable",100, 149,  6.4, 33.1,  0.5),
        ("Zucchini",            "vegetable",100,  17,  1.2,  3.1,  0.3),
        ("Mushrooms",           "vegetable",100,  22,  3.1,  3.3,  0.3),
        ("Kale",                "vegetable",100,  35,  2.9,  4.4,  1.5),
        ("Cauliflower",         "vegetable",100,  25,  1.9,  5.0,  0.3),
        ("Cabbage",             "vegetable",100,  25,  1.3,  5.8,  0.1),
        ("Brussels Sprouts",    "vegetable",100,  43,  3.4,  9.0,  0.3),
        ("Asparagus",           "vegetable",100,  20,  2.2,  3.9,  0.1),
        ("Green Beans",         "vegetable",100,  31,  1.8,  7.0,  0.1),
        ("Celery",              "vegetable",100,  16,  0.7,  3.0,  0.2),
        ("Lettuce",             "vegetable",100,  15,  1.4,  2.9,  0.2),
        ("Corn",                "vegetable",100,  96,  3.4, 21.0,  1.5),
        # Dairy
        ("Milk (whole)",        "dairy",   240, 149,  8.0, 12.0,  8.0),
        ("Milk (skim)",         "dairy",   240,  83,  8.0, 12.0,  0.2),
        ("Milk (2%)",           "dairy",   240, 122,  8.0, 12.0,  4.8),
        ("Cheddar Cheese",      "dairy",    28, 113,  7.0,  0.4,  9.0),
        ("Swiss Cheese",        "dairy",    28, 106,  8.0,  1.5,  8.0),
        ("Mozzarella",          "dairy",    28,  85,  6.0,  1.0,  6.0),
        ("Butter",              "dairy",    14, 102,  0.1,  0.0, 11.5),
        ("Parmesan",            "dairy",    28, 111, 10.0,  1.0,  7.0),
        ("Kefir",               "dairy",   240, 104,  9.0, 12.0,  2.0),
        ("Yogurt (plain)",      "dairy",   170, 100,  9.0,  6.0,  3.0),
        ("Yogurt (Greek vanilla)","dairy",170, 120, 11.0, 14.0,  0.0),
        ("Ricotta",             "dairy",   124, 216, 14.0,  4.0, 16.0),
        ("Cream Cheese",        "dairy",    28,  99,  2.0,  2.0, 10.0),
        ("Cottage Cheese 2%",   "dairy",   100,  81, 11.0,  3.0,  2.0),
        ("Protein Pudding",     "dairy",   100, 110, 12.0,  8.0,  3.0),
        # Fat
        ("Olive Oil",           "fat",      14, 119,  0.0,  0.0, 13.5),
        ("Almonds",             "fat",      28, 164,  6.0,  6.0, 14.0),
        ("Mixed Nuts",          "fat",      28, 170,  5.0,  6.0, 15.0),
        ("Peanut Butter",       "fat",      32, 188,  8.0,  7.0, 16.0),
        ("Avocado Oil",         "fat",      14, 120,  0.0,  0.0, 14.0),
        ("Walnuts",             "fat",      28, 185,  4.3,  3.9, 18.5),
        ("Cashews",             "fat",      28, 157,  5.2,  8.6, 12.4),
        ("Chia Seeds",          "fat",      28, 138,  4.7, 12.0,  8.7),
        ("Flax Seeds",          "fat",      10,  53,  1.8,  2.9,  4.2),
        ("Tahini",              "fat",      15,  89,  2.6,  3.2,  8.1),
        ("Sunflower Seeds",     "fat",      28, 164,  6.0,  6.0, 14.0),
        ("Pumpkin Seeds",       "fat",      28, 151,  7.0,  4.0, 13.0),
        ("Pistachios",          "fat",      28, 159,  6.0,  8.0, 13.0),
        # Snack
        ("Dark Chocolate",      "snack",    28, 170,  2.0, 13.0, 12.0),
        ("Granola Bar",         "snack",    45, 193,  4.0, 29.0,  7.0),
        ("Protein Cookie",      "snack",    60, 220, 12.0, 20.0, 10.0),
        ("Pizza Slice",         "snack",   107, 285, 12.0, 36.0, 10.0),
        ("Burger Patty",        "snack",   100, 254, 26.0,  0.0, 17.0),
        ("French Fries",        "snack",   100, 312,  3.4, 41.0, 15.0),
        ("Apple Chips",         "snack",    30, 130,  1.0, 26.0,  2.0),
        ("Beef Jerky Snack",    "snack",    28,  90, 11.0,  3.0,  2.0),
        ("Pretzels",            "snack",    28, 108,  2.8, 22.0,  0.8),
        ("Popcorn (air-popped)","snack",     8,  31,  1.0,  6.0,  0.4),
        ("Trail Mix",           "snack",    30, 140,  4.0, 12.0,  9.0),
        ("Rice Cakes",          "snack",     9,  35,  0.7,  7.3,  0.3),
        ("Granola Cluster",     "snack",    30, 150,  4.0, 20.0,  6.0),
        ("Crackers",            "snack",    30, 130,  2.0, 22.0,  4.0),
        ("Chocolate Bar",       "snack",    43, 210,  2.0, 24.0, 11.0),
        ("Protein Chips",       "snack",    28, 140, 14.0,  4.0,  7.0),
        # Beverage
        ("Orange Juice",        "beverage",240, 112,  1.7, 26.0,  0.5),
        ("Coffee (black)",      "beverage",240,   2,  0.3,  0.0,  0.0),
        ("Coffee (latte)",      "beverage",240, 130,  8.0, 12.0,  5.0),
        ("Apple Juice",         "beverage",240, 114,  0.2, 28.0,  0.3),
        ("Coconut Water",       "beverage",240,  45,  1.7,  9.0,  0.5),
        ("Green Tea",           "beverage",240,   2,  0.0,  0.0,  0.0),
        ("Black Tea",           "beverage",240,   2,  0.0,  0.0,  0.0),
        ("Sparkling Water",     "beverage",240,   0,  0.0,  0.0,  0.0),
        ("Sports Drink",        "beverage",240,  50,  0.0, 14.0,  0.0),
        ("Iced Tea",            "beverage",240,  90,  0.0, 23.0,  0.0),
        ("Milkshake",           "beverage",240, 290,  8.0, 39.0, 12.0),
        ("Protein Coffee",      "beverage",240, 160, 20.0, 10.0,  3.0),
        ("Electrolyte Drink",   "beverage",240,  20,  0.0,  5.0,  0.0),
    ]
    category_micro_profiles = {
        "protein": {"vitamin_a_mcg": 20.0, "vitamin_c_mg": 0.0, "vitamin_d_mcg": 0.8, "vitamin_b12_mcg": 0.9, "calcium_mg": 25.0, "iron_mg": 1.2, "potassium_mg": 320.0},
        "grain": {"vitamin_a_mcg": 0.0, "vitamin_c_mg": 0.0, "vitamin_d_mcg": 0.0, "vitamin_b12_mcg": 0.0, "calcium_mg": 18.0, "iron_mg": 2.2, "potassium_mg": 160.0},
        "fruit": {"vitamin_a_mcg": 35.0, "vitamin_c_mg": 28.0, "vitamin_d_mcg": 0.0, "vitamin_b12_mcg": 0.0, "calcium_mg": 20.0, "iron_mg": 0.3, "potassium_mg": 220.0},
        "vegetable": {"vitamin_a_mcg": 230.0, "vitamin_c_mg": 38.0, "vitamin_d_mcg": 0.0, "vitamin_b12_mcg": 0.0, "calcium_mg": 55.0, "iron_mg": 1.4, "potassium_mg": 290.0},
        "dairy": {"vitamin_a_mcg": 70.0, "vitamin_c_mg": 0.8, "vitamin_d_mcg": 1.2, "vitamin_b12_mcg": 0.6, "calcium_mg": 220.0, "iron_mg": 0.1, "potassium_mg": 170.0},
        "fat": {"vitamin_a_mcg": 12.0, "vitamin_c_mg": 0.0, "vitamin_d_mcg": 0.0, "vitamin_b12_mcg": 0.0, "calcium_mg": 22.0, "iron_mg": 1.0, "potassium_mg": 210.0},
        "snack": {"vitamin_a_mcg": 10.0, "vitamin_c_mg": 1.0, "vitamin_d_mcg": 0.1, "vitamin_b12_mcg": 0.2, "calcium_mg": 35.0, "iron_mg": 1.5, "potassium_mg": 170.0},
        "beverage": {"vitamin_a_mcg": 6.0, "vitamin_c_mg": 7.0, "vitamin_d_mcg": 0.2, "vitamin_b12_mcg": 0.1, "calcium_mg": 22.0, "iron_mg": 0.1, "potassium_mg": 120.0},
        "other": {"vitamin_a_mcg": 10.0, "vitamin_c_mg": 4.0, "vitamin_d_mcg": 0.1, "vitamin_b12_mcg": 0.2, "calcium_mg": 25.0, "iron_mg": 0.8, "potassium_mg": 160.0},
    }

    def micro_for_food(category: str, grams: float) -> dict[str, float]:
        profile = category_micro_profiles.get(category, category_micro_profiles["other"])
        factor = max(1.0, float(grams)) / 100.0
        return {k: round(v * factor, 2) for k, v in profile.items()}

    async with AsyncSessionLocal() as session:
        # Clear and re-seed preset foods (preserves custom user foods)
        from sqlalchemy import delete
        await session.execute(delete(FoodItem).where(FoodItem.user_id.is_(None)))
        for name, cat, grams, cal, prot, carbs, fat in foods:
            micro = micro_for_food(cat, grams)
            session.add(FoodItem(
                name=name, category=cat, base_grams=float(grams), serving_desc=f"{int(grams)}g",
                calories=cal, protein_g=prot, carbs_g=carbs, fat_g=fat,
                vitamin_a_mcg=micro["vitamin_a_mcg"],
                vitamin_c_mg=micro["vitamin_c_mg"],
                vitamin_d_mcg=micro["vitamin_d_mcg"],
                vitamin_b12_mcg=micro["vitamin_b12_mcg"],
                calcium_mg=micro["calcium_mg"],
                iron_mg=micro["iron_mg"],
                potassium_mg=micro["potassium_mg"],
                user_id=None,
            ))
        await session.commit()


async def seed_exercise_catalog() -> None:
    seed_data = [
        ("Bench Press", ExerciseType.weighted, MuscleGroup.chest),
        ("Incline Dumbbell Press", ExerciseType.weighted, MuscleGroup.chest),
        ("Push-Up", ExerciseType.bodyweight, MuscleGroup.chest),
        ("Cable Fly", ExerciseType.weighted, MuscleGroup.chest),
        ("Chest Dip", ExerciseType.bodyweight, MuscleGroup.chest),
        ("Barbell Row", ExerciseType.weighted, MuscleGroup.back),
        ("Pull-Up", ExerciseType.bodyweight, MuscleGroup.back),
        ("Decline Bench Press", ExerciseType.weighted, MuscleGroup.chest),
        ("Dumbbell Fly", ExerciseType.weighted, MuscleGroup.chest),
        ("Machine Chest Press", ExerciseType.weighted, MuscleGroup.chest),
        ("Lat Pulldown", ExerciseType.weighted, MuscleGroup.back),
        ("Seated Cable Row", ExerciseType.weighted, MuscleGroup.back),
        ("Straight-Arm Pulldown", ExerciseType.weighted, MuscleGroup.back),
        ("Overhead Press", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Lateral Raise", ExerciseType.weighted, MuscleGroup.shoulders),
        ("One-Arm Dumbbell Row", ExerciseType.weighted, MuscleGroup.back),
        ("Chest-Supported Row", ExerciseType.weighted, MuscleGroup.back),
        ("Face Pull", ExerciseType.weighted, MuscleGroup.back),
        ("Rear Delt Fly", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Arnold Press", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Dumbbell Curl", ExerciseType.weighted, MuscleGroup.biceps),
        ("Hammer Curl", ExerciseType.weighted, MuscleGroup.biceps),
        ("Front Raise", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Upright Row", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Machine Shoulder Press", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Preacher Curl", ExerciseType.weighted, MuscleGroup.biceps),
        ("Tricep Pushdown", ExerciseType.weighted, MuscleGroup.triceps),
        ("Dip", ExerciseType.bodyweight, MuscleGroup.triceps),
        ("Incline Curl", ExerciseType.weighted, MuscleGroup.biceps),
        ("Cable Curl", ExerciseType.weighted, MuscleGroup.biceps),
        ("Concentration Curl", ExerciseType.weighted, MuscleGroup.biceps),
        ("Skull Crusher", ExerciseType.weighted, MuscleGroup.triceps),
        ("Squat", ExerciseType.weighted, MuscleGroup.quads),
        ("Leg Press", ExerciseType.weighted, MuscleGroup.quads),
        ("Overhead Tricep Extension", ExerciseType.weighted, MuscleGroup.triceps),
        ("Close-Grip Bench Press", ExerciseType.weighted, MuscleGroup.triceps),
        ("Bench Dips", ExerciseType.bodyweight, MuscleGroup.triceps),
        ("Lunge", ExerciseType.bodyweight, MuscleGroup.quads),
        ("Leg Extension", ExerciseType.weighted, MuscleGroup.quads),
        ("Romanian Deadlift", ExerciseType.weighted, MuscleGroup.hamstrings),
        ("Leg Curl", ExerciseType.weighted, MuscleGroup.hamstrings),
        ("Front Squat", ExerciseType.weighted, MuscleGroup.quads),
        ("Hack Squat", ExerciseType.weighted, MuscleGroup.quads),
        ("Step-Up", ExerciseType.bodyweight, MuscleGroup.quads),
        ("Good Morning", ExerciseType.weighted, MuscleGroup.hamstrings),
        ("Hip Thrust", ExerciseType.weighted, MuscleGroup.glutes),
        ("Glute Bridge", ExerciseType.bodyweight, MuscleGroup.glutes),
        ("Stiff-Leg Deadlift", ExerciseType.weighted, MuscleGroup.hamstrings),
        ("Nordic Curl", ExerciseType.bodyweight, MuscleGroup.hamstrings),
        ("Bulgarian Split Squat", ExerciseType.weighted, MuscleGroup.glutes),
        ("Plank", ExerciseType.bodyweight, MuscleGroup.core),
        ("Sit-Up", ExerciseType.bodyweight, MuscleGroup.core),
        ("Cable Kickback", ExerciseType.weighted, MuscleGroup.glutes),
        ("Hip Abduction Machine", ExerciseType.weighted, MuscleGroup.glutes),
        ("Hanging Leg Raise", ExerciseType.bodyweight, MuscleGroup.core),
        ("Russian Twist", ExerciseType.bodyweight, MuscleGroup.core),
        ("Calf Raise", ExerciseType.weighted, MuscleGroup.calves),
        ("Farmer Carry", ExerciseType.weighted, MuscleGroup.forearms),
        ("Cable Crunch", ExerciseType.weighted, MuscleGroup.core),
        ("Ab Wheel Rollout", ExerciseType.bodyweight, MuscleGroup.core),
        ("Dead Bug", ExerciseType.bodyweight, MuscleGroup.core),
        ("Burpee", ExerciseType.bodyweight, MuscleGroup.full_body),
        ("Seated Calf Raise", ExerciseType.weighted, MuscleGroup.calves),
        ("Standing Calf Raise", ExerciseType.weighted, MuscleGroup.calves),
        ("Deadlift", ExerciseType.weighted, MuscleGroup.full_body),
        ("Wrist Curl", ExerciseType.weighted, MuscleGroup.forearms),
        ("Reverse Wrist Curl", ExerciseType.weighted, MuscleGroup.forearms),
        ("Kettlebell Swing", ExerciseType.weighted, MuscleGroup.full_body),
        ("Running", ExerciseType.cardio, MuscleGroup.cardio),
        ("Cycling", ExerciseType.cardio, MuscleGroup.cardio),
        ("Thruster", ExerciseType.weighted, MuscleGroup.full_body),
        ("Clean and Press", ExerciseType.weighted, MuscleGroup.full_body),
        ("Medicine Ball Slam", ExerciseType.bodyweight, MuscleGroup.full_body),
        ("Jumping Jacks", ExerciseType.bodyweight, MuscleGroup.full_body),
        ("High Knees", ExerciseType.bodyweight, MuscleGroup.full_body),
        ("Mountain Climbers", ExerciseType.bodyweight, MuscleGroup.full_body),
        ("Sandbag Carry", ExerciseType.weighted, MuscleGroup.full_body),
        ("Rowing Machine", ExerciseType.cardio, MuscleGroup.cardio),
        ("Jump Rope", ExerciseType.cardio, MuscleGroup.cardio),
        ("Swimming", ExerciseType.cardio, MuscleGroup.cardio),
        ("Elliptical", ExerciseType.cardio, MuscleGroup.cardio),
        ("Stair Climber", ExerciseType.cardio, MuscleGroup.cardio),
        ("Treadmill Walk", ExerciseType.cardio, MuscleGroup.cardio),
        ("Sled Push", ExerciseType.weighted, MuscleGroup.full_body),
        ("Battle Ropes", ExerciseType.cardio, MuscleGroup.full_body),
        ("Treadmill Run", ExerciseType.cardio, MuscleGroup.cardio),
        ("Incline Walk", ExerciseType.cardio, MuscleGroup.cardio),
        ("Outdoor Hike", ExerciseType.cardio, MuscleGroup.cardio),
        ("Mountain Bike", ExerciseType.cardio, MuscleGroup.cardio),
        ("Spin Bike", ExerciseType.cardio, MuscleGroup.cardio),
        ("Arc Trainer", ExerciseType.cardio, MuscleGroup.cardio),
        ("Ski Erg", ExerciseType.cardio, MuscleGroup.cardio),
        ("Boxing", ExerciseType.cardio, MuscleGroup.cardio),
        ("Shadow Boxing", ExerciseType.cardio, MuscleGroup.cardio),
        ("Battle Ropes", ExerciseType.cardio, MuscleGroup.full_body),
        ("Sled Push", ExerciseType.weighted, MuscleGroup.full_body),
        ("Sled Pull", ExerciseType.weighted, MuscleGroup.full_body),
    ]

    async with AsyncSessionLocal() as session:
        existing_rows = await session.execute(select(ExerciseCatalog.name))
        existing_names = {row[0] for row in existing_rows.all()}
        seen_names = set(existing_names)
        for name, ex_type, muscle in seed_data:
            # Prevent duplicate inserts both against DB rows and duplicates in seed_data.
            if name in seen_names:
                continue
            session.add(
                ExerciseCatalog(name=name, exercise_type=ex_type, muscle_group=muscle)
            )
            seen_names.add(name)
        await session.commit()


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
