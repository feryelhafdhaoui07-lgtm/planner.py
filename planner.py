import json
import os
import tkinter as tk
from datetime import date as dt_date, datetime
from tkinter import ttk, messagebox


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "tasks.json")

PRIORITY_ORDER = {"Haute": 0, "Moyenne": 1, "Basse": 2}
tasks = []


def save_tasks():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    except OSError:
        messagebox.showerror("Erreur", "Impossible de sauvegarder les tâches.")


def load_tasks():
    global tasks
    if not os.path.exists(DATA_FILE):
        tasks = []
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)
    except (OSError, json.JSONDecodeError):
        tasks = []
    
    for t in tasks:
        t.setdefault("temps_reel", 0)



def format_seconds(seconds):
    """Affiche des secondes en 'X min' ou 'H h MM min'."""
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60:02d} min"


def find_index(task):
    """Retrouve l'index réel d'une tâche (comparaison par identité)."""
    for i, t in enumerate(tasks):
        if t is task:
            return i
    return None



def sort_key(item):
    _, t = item
    return (t["statut"] == "Terminée", PRIORITY_ORDER.get(t["priorite"], 1), t["date"])


def refresh_table():
    for row in tree_tasks.get_children():
        tree_tasks.delete(row)

    today = dt_date.today().isoformat()
    items = list(enumerate(tasks))
    if var_today.get():
        items = [(i, t) for i, t in items if t["date"] == today]

    for i, t in sorted(items, key=sort_key):
        tag = "done" if t["statut"] == "Terminée" else t["priorite"]
        tree_tasks.insert(
            "", tk.END, iid=str(i),
            values=(t["titre"], t["date"], f'{t["duree"]} min',
                    format_seconds(t["temps_reel"]), t["priorite"], t["statut"]),
            tags=(tag,),
        )
    update_stats()


def refresh_row(task):
    """Met à jour seulement la colonne 'Réel' d'une tâche (sans perdre la sélection)."""
    i = find_index(task)
    if i is not None and tree_tasks.exists(str(i)):
        tree_tasks.set(str(i), "reel", format_seconds(task["temps_reel"]))
    update_stats()


def update_stats():
    today = dt_date.today().isoformat()
    day_tasks = [t for t in tasks if t["date"] == today]
    remaining_min = sum(t["duree"] for t in day_tasks if t["statut"] != "Terminée")
    done = sum(1 for t in day_tasks if t["statut"] == "Terminée")
    percent = round(done / len(day_tasks) * 100) if day_tasks else 0
    worked = sum(t["temps_reel"] for t in day_tasks)
    lbl_stats["text"] = (
        f"Aujourd'hui : {done}/{len(day_tasks)} terminées ({percent}%)\n"
        f"Reste à faire (estimé) : {format_seconds(remaining_min * 60)}   |   "
        f"Temps travaillé : {format_seconds(worked)}"
    )



def add_task(event=None):
    title = ent_title.get().strip()
    date_text = ent_date.get().strip()
    priority = cmb_priority.get()

    if title == "":
        messagebox.showerror("Erreur", "Le titre ne peut pas être vide.")
        return

    try:
        duration = int(ent_duration.get())
        if duration <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Erreur", "La durée doit être un nombre entier positif.")
        return

    if date_text == "":
        date_text = dt_date.today().isoformat()
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        messagebox.showerror("Erreur", "Date invalide. Format attendu : AAAA-MM-JJ.")
        return

    tasks.append({
        "titre": title,
        "date": date_text,
        "duree": duration,
        "temps_reel": 0,
        "priorite": priority,
        "statut": "À faire",
    })
    save_tasks()
    refresh_table()

    ent_title.delete(0, tk.END)
    ent_duration.delete(0, tk.END)
    ent_title.focus()


def get_selected_index():
    selected = tree_tasks.selection()
    if not selected:
        messagebox.showwarning("Attention", "Sélectionnez une tâche d'abord.")
        return None
    return int(selected[0])


def delete_task():
    index = get_selected_index()
    if index is None:
        return
    if tasks[index] is active_task:
        reset_timer()                      # on arrête le minuteur de cette tâche
    tasks.pop(index)
    save_tasks()
    refresh_table()


def done_task():
    index = get_selected_index()
    if index is None:
        return
    if tasks[index]["statut"] == "Terminée":
        tasks[index]["statut"] = "À faire"
    else:
        tasks[index]["statut"] = "Terminée"
    save_tasks()
    refresh_table()



WORK_SECONDS = 25 * 60
remaining = WORK_SECONDS
timer_running = False
timer_job = None
active_task = None        


def update_timer():
    global remaining, timer_running, timer_job, tick_count, active_task
    remaining -= 1

    
    if active_task is not None:
        active_task["temps_reel"] += 1
        tick_count += 1
        refresh_row(active_task)
        if tick_count % 30 == 0:           
            save_tasks()

    mins, secs = divmod(remaining, 60)
    lbl_timer["text"] = f"{mins:02d}:{secs:02d}"

    if remaining > 0:
        timer_job = window.after(1000, update_timer)
    else:
        timer_running = False
        timer_job = None
        remaining = WORK_SECONDS
        btn_start["text"] = "Démarrer"
        lbl_timer["text"] = "25:00"
        lbl_active["text"] = "Aucune tâche en cours"
        active_task = None
        save_tasks()
        window.bell()
        messagebox.showinfo("Pomodoro", "Temps écoulé ! Faites une pause de 5 minutes.")


def start_timer():
    global timer_running, timer_job, active_task

    if timer_running:                       
        window.after_cancel(timer_job)
        timer_running = False
        btn_start["text"] = "Reprendre"
        save_tasks()
        return

    
    selected = tree_tasks.selection()
    if selected:
        active_task = tasks[int(selected[0])]
    elif active_task is None:
        messagebox.showwarning("Attention",
                               "Sélectionnez la tâche sur laquelle vous allez travailler.")
        return

    lbl_active["text"] = f"En cours : {active_task['titre']}"
    timer_running = True
    btn_start["text"] = "Pause"
    timer_job = window.after(1000, update_timer)


def reset_timer():
    global remaining, timer_running, timer_job, active_task
    if timer_job is not None:
        window.after_cancel(timer_job)
        timer_job = None
    timer_running = False
    remaining = WORK_SECONDS
    active_task = None
    lbl_timer["text"] = "25:00"
    lbl_active["text"] = "Aucune tâche en cours"
    btn_start["text"] = "Démarrer"
    save_tasks()


def on_close():
    save_tasks()
    window.destroy()



window = tk.Tk()
window.title("Planificateur Personnel")
window.resizable(width=False, height=False)


frm_form = tk.Frame(master=window)
tk.Label(master=frm_form, text="Tâche :").grid(row=0, column=0, sticky="e")
ent_title = tk.Entry(master=frm_form, width=28)
ent_title.grid(row=0, column=1, padx=5, pady=2)

tk.Label(master=frm_form, text="Date (AAAA-MM-JJ) :").grid(row=1, column=0, sticky="e")
ent_date = tk.Entry(master=frm_form, width=12)
ent_date.insert(0, dt_date.today().isoformat())
ent_date.grid(row=1, column=1, padx=5, pady=2, sticky="w")

tk.Label(master=frm_form, text="Durée estimée (min) :").grid(row=2, column=0, sticky="e")
ent_duration = tk.Entry(master=frm_form, width=6)
ent_duration.grid(row=2, column=1, padx=5, pady=2, sticky="w")

tk.Label(master=frm_form, text="Priorité :").grid(row=3, column=0, sticky="e")
cmb_priority = ttk.Combobox(master=frm_form, values=["Haute", "Moyenne", "Basse"],
                            width=10, state="readonly")
cmb_priority.set("Moyenne")
cmb_priority.grid(row=3, column=1, padx=5, pady=2, sticky="w")

btn_add = tk.Button(master=frm_form, text="Ajouter", command=add_task)
btn_add.grid(row=4, column=1, pady=5, sticky="w")
frm_form.grid(row=0, column=0, padx=10, pady=10)


var_today = tk.BooleanVar(value=False)
chk_today = tk.Checkbutton(master=window, text="Afficher seulement les tâches d'aujourd'hui",
                           variable=var_today, command=lambda: refresh_table())
chk_today.grid(row=1, column=0, sticky="w", padx=10)


columns = ("titre", "date", "estime", "reel", "priorite", "statut")
tree_tasks = ttk.Treeview(master=window, columns=columns, show="headings", height=10)
for col, text, width in (("titre", "Tâche", 170), ("date", "Date", 85),
                         ("estime", "Estimé", 65), ("reel", "Réel", 70),
                         ("priorite", "Priorité", 70), ("statut", "Statut", 80)):
    tree_tasks.heading(col, text=text)
    tree_tasks.column(col, width=width)
tree_tasks.tag_configure("Haute", foreground="#c0392b")
tree_tasks.tag_configure("Moyenne", foreground="#d68910")
tree_tasks.tag_configure("Basse", foreground="#1e8449")
tree_tasks.tag_configure("done", foreground="#999999")
tree_tasks.grid(row=2, column=0, padx=10)


frm_actions = tk.Frame(master=window)
btn_done = tk.Button(master=frm_actions, text="Terminée / À faire", command=done_task)
btn_delete = tk.Button(master=frm_actions, text="Supprimer", command=delete_task)
btn_done.grid(row=0, column=0, padx=5)
btn_delete.grid(row=0, column=1, padx=5)
frm_actions.grid(row=3, column=0, pady=8)


lbl_stats = tk.Label(master=window, text="")
lbl_stats.grid(row=4, column=0)


frm_timer = tk.Frame(master=window)
lbl_active = tk.Label(master=frm_timer, text="Aucune tâche en cours", fg="#555555")
lbl_timer = tk.Label(master=frm_timer, text="25:00", font=("Arial", 24))
btn_start = tk.Button(master=frm_timer, text="Démarrer", command=start_timer)
btn_reset = tk.Button(master=frm_timer, text="Réinitialiser", command=reset_timer)
lbl_active.grid(row=0, column=0, columnspan=2)
lbl_timer.grid(row=1, column=0, columnspan=2)
btn_start.grid(row=2, column=0, padx=5, pady=5)
btn_reset.grid(row=2, column=1, padx=5, pady=5)
frm_timer.grid(row=5, column=0, pady=10)

ent_title.bind("<Return>", add_task)


load_tasks()
refresh_table()
window.protocol("WM_DELETE_WINDOW", on_close)
window.mainloop()