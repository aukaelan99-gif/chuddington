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

        # food_items category column
        fi_info = await conn.execute(text("PRAGMA table_info(food_items)"))
        fi_cols = {row[1] for row in fi_info.fetchall()}
        if "category" not in fi_cols:
            await conn.execute(text("ALTER TABLE food_items ADD COLUMN category VARCHAR DEFAULT 'other'"))
        if "base_grams" not in fi_cols:
            await conn.execute(text("ALTER TABLE food_items ADD COLUMN base_grams REAL DEFAULT 100"))

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
        # Grain
        ("White Rice (cooked)", "grain",   100, 130,  2.7, 28.0,  0.3),
        ("Brown Rice (cooked)", "grain",   100, 112,  2.6, 23.0,  0.9),
        ("Oats (dry)",          "grain",   100, 389, 17.0, 66.0,  7.0),
        ("White Bread",         "grain",    30,  79,  2.7, 15.0,  1.0),
        ("Whole Wheat Bread",   "grain",    30,  81,  4.0, 13.8,  1.1),
        ("Pasta (cooked)",      "grain",   100, 131,  5.0, 25.0,  1.1),
        ("Sweet Potato",        "grain",   100,  86,  1.6, 20.0,  0.1),
        ("Potato",              "grain",   100,  77,  2.0, 17.0,  0.1),
        ("Quinoa (cooked)",     "grain",   100, 120,  4.4, 21.0,  1.9),
        ("Bagel",               "grain",    95, 270, 11.0, 53.0,  1.5),
        ("Tortilla (flour)",    "grain",    49, 146,  3.8, 25.0,  3.5),
        ("Couscous (cooked)",   "grain",   100, 112,  3.8, 23.0,  0.2),
        ("Barley (cooked)",     "grain",   100, 123,  2.3, 28.0,  0.4),
        ("Rice Noodles (cooked)","grain",  100, 109,  1.8, 24.0,  0.2),
        ("Corn (cooked)",       "grain",   100,  96,  3.4, 21.0,  1.5),
        ("Granola",             "grain",   100, 471, 10.0, 64.0, 20.0),
        # Fruit
        ("Banana",              "fruit",   118, 105,  1.3, 27.0,  0.4),
        ("Apple",               "fruit",   182,  95,  0.5, 25.0,  0.3),
        ("Orange",              "fruit",   131,  62,  1.2, 15.0,  0.2),
        ("Blueberries",         "fruit",   100,  57,  0.7, 14.0,  0.3),
        ("Strawberries",        "fruit",   100,  32,  0.7,  7.7,  0.3),
        ("Mango",               "fruit",   100,  60,  0.8, 15.0,  0.4),
        ("Grapes",              "fruit",   100,  69,  0.7, 18.0,  0.2),
        ("Pineapple",           "fruit",   100,  50,  0.5, 13.0,  0.1),
        ("Kiwi",                "fruit",   100,  61,  1.1, 15.0,  0.5),
        ("Pear",                "fruit",   178, 101,  0.6, 27.0,  0.2),
        ("Watermelon",          "fruit",   100,  30,  0.6,  7.6,  0.2),
        # Vegetable
        ("Broccoli",            "vegetable",100,  34,  2.8,  7.0,  0.4),
        ("Spinach",             "vegetable",100,  23,  2.9,  3.6,  0.4),
        ("Avocado",             "vegetable",100, 160,  2.0,  8.5, 14.7),
        ("Carrot",              "vegetable",100,  41,  0.9, 10.0,  0.2),
        ("Cucumber",            "vegetable",100,  15,  0.7,  3.6,  0.1),
        ("Bell Pepper",         "vegetable",100,  31,  1.0,  6.0,  0.3),
        ("Zucchini",            "vegetable",100,  17,  1.2,  3.1,  0.3),
        ("Mushrooms",           "vegetable",100,  22,  3.1,  3.3,  0.3),
        ("Kale",                "vegetable",100,  35,  2.9,  4.4,  1.5),
        # Dairy
        ("Milk (whole)",        "dairy",   240, 149,  8.0, 12.0,  8.0),
        ("Milk (skim)",         "dairy",   240,  83,  8.0, 12.0,  0.2),
        ("Cheddar Cheese",      "dairy",    28, 113,  7.0,  0.4,  9.0),
        ("Mozzarella",          "dairy",    28,  85,  6.0,  1.0,  6.0),
        ("Butter",              "dairy",    14, 102,  0.1,  0.0, 11.5),
        ("Parmesan",            "dairy",    28, 111, 10.0,  1.0,  7.0),
        ("Kefir",               "dairy",   240, 104,  9.0, 12.0,  2.0),
        ("Ricotta",             "dairy",   124, 216, 14.0,  4.0, 16.0),
        # Fat
        ("Olive Oil",           "fat",      14, 119,  0.0,  0.0, 13.5),
        ("Almonds",             "fat",      28, 164,  6.0,  6.0, 14.0),
        ("Peanut Butter",       "fat",      32, 188,  8.0,  7.0, 16.0),
        ("Walnuts",             "fat",      28, 185,  4.3,  3.9, 18.5),
        ("Cashews",             "fat",      28, 157,  5.2,  8.6, 12.4),
        ("Chia Seeds",          "fat",      28, 138,  4.7, 12.0,  8.7),
        ("Flax Seeds",          "fat",      10,  53,  1.8,  2.9,  4.2),
        ("Tahini",              "fat",      15,  89,  2.6,  3.2,  8.1),
        # Snack
        ("Dark Chocolate",      "snack",    28, 170,  2.0, 13.0, 12.0),
        ("Granola Bar",         "snack",    45, 193,  4.0, 29.0,  7.0),
        ("Pizza Slice",         "snack",   107, 285, 12.0, 36.0, 10.0),
        ("Burger Patty",        "snack",   100, 254, 26.0,  0.0, 17.0),
        ("French Fries",        "snack",   100, 312,  3.4, 41.0, 15.0),
        ("Pretzels",            "snack",    28, 108,  2.8, 22.0,  0.8),
        ("Popcorn (air-popped)","snack",     8,  31,  1.0,  6.0,  0.4),
        ("Trail Mix",           "snack",    30, 140,  4.0, 12.0,  9.0),
        ("Rice Cakes",          "snack",     9,  35,  0.7,  7.3,  0.3),
        # Beverage
        ("Orange Juice",        "beverage",240, 112,  1.7, 26.0,  0.5),
        ("Coffee (black)",      "beverage",240,   2,  0.3,  0.0,  0.0),
        ("Apple Juice",         "beverage",240, 114,  0.2, 28.0,  0.3),
        ("Coconut Water",       "beverage",240,  45,  1.7,  9.0,  0.5),
        ("Green Tea",           "beverage",240,   2,  0.0,  0.0,  0.0),
        ("Sports Drink",        "beverage",240,  50,  0.0, 14.0,  0.0),
    ]
    async with AsyncSessionLocal() as session:
        # Clear and re-seed preset foods (preserves custom user foods)
        from sqlalchemy import delete
        await session.execute(delete(FoodItem).where(FoodItem.user_id.is_(None)))
        for name, cat, grams, cal, prot, carbs, fat in foods:
            session.add(FoodItem(
                name=name, category=cat, base_grams=float(grams), serving_desc=f"{int(grams)}g",
                calories=cal, protein_g=prot, carbs_g=carbs, fat_g=fat,
                user_id=None,
            ))
        await session.commit()


async def seed_exercise_catalog() -> None:
    seed_data = [
        ("Bench Press", ExerciseType.weighted, MuscleGroup.chest),
        ("Incline Dumbbell Press", ExerciseType.weighted, MuscleGroup.chest),
        ("Push-Up", ExerciseType.bodyweight, MuscleGroup.chest),
        ("Barbell Row", ExerciseType.weighted, MuscleGroup.back),
        ("Pull-Up", ExerciseType.bodyweight, MuscleGroup.back),
        ("Lat Pulldown", ExerciseType.weighted, MuscleGroup.back),
        ("Overhead Press", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Lateral Raise", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Rear Delt Fly", ExerciseType.weighted, MuscleGroup.shoulders),
        ("Dumbbell Curl", ExerciseType.weighted, MuscleGroup.biceps),
        ("Hammer Curl", ExerciseType.weighted, MuscleGroup.biceps),
        ("Tricep Pushdown", ExerciseType.weighted, MuscleGroup.triceps),
        ("Dip", ExerciseType.bodyweight, MuscleGroup.triceps),
        ("Squat", ExerciseType.weighted, MuscleGroup.quads),
        ("Leg Press", ExerciseType.weighted, MuscleGroup.quads),
        ("Lunge", ExerciseType.bodyweight, MuscleGroup.quads),
        ("Romanian Deadlift", ExerciseType.weighted, MuscleGroup.hamstrings),
        ("Leg Curl", ExerciseType.weighted, MuscleGroup.hamstrings),
        ("Hip Thrust", ExerciseType.weighted, MuscleGroup.glutes),
        ("Glute Bridge", ExerciseType.bodyweight, MuscleGroup.glutes),
        ("Plank", ExerciseType.bodyweight, MuscleGroup.core),
        ("Sit-Up", ExerciseType.bodyweight, MuscleGroup.core),
        ("Hanging Leg Raise", ExerciseType.bodyweight, MuscleGroup.core),
        ("Calf Raise", ExerciseType.weighted, MuscleGroup.calves),
        ("Farmer Carry", ExerciseType.weighted, MuscleGroup.forearms),
        ("Burpee", ExerciseType.bodyweight, MuscleGroup.full_body),
        ("Deadlift", ExerciseType.weighted, MuscleGroup.full_body),
        ("Running", ExerciseType.cardio, MuscleGroup.cardio),
        ("Cycling", ExerciseType.cardio, MuscleGroup.cardio),
        ("Rowing Machine", ExerciseType.cardio, MuscleGroup.cardio),
        ("Jump Rope", ExerciseType.cardio, MuscleGroup.cardio),
        ("Swimming", ExerciseType.cardio, MuscleGroup.cardio),
        ("Elliptical", ExerciseType.cardio, MuscleGroup.cardio),
        ("Stair Climber", ExerciseType.cardio, MuscleGroup.cardio),
    ]

    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count(ExerciseCatalog.id)))
        if (count or 0) > 0:
            return
        for name, ex_type, muscle in seed_data:
            session.add(
                ExerciseCatalog(name=name, exercise_type=ex_type, muscle_group=muscle)
            )
        await session.commit()


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
