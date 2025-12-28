document.addEventListener("DOMContentLoaded", function() {
    const taskInput = document.getElementById("task-input");
    const taskForm = document.getElementById("task-form");
    const taskList = document.getElementById("task-list");
    const taskEmptyState = document.getElementById("task-empty-state");
    const clearCompletedBtn = document.getElementById("clear-completed");
    
    // Load tasks from SessionStorage on page load
    loadTasks();
    
    // Event listeners for task operations
    taskForm.addEventListener("submit", function(event) {
        event.preventDefault();
        addNewTask();
    });
    
    clearCompletedBtn.addEventListener("click", clearCompletedTasks);
    
    function addNewTask() {
        const taskText = taskInput.value.trim();
        if (taskText) {
            const task = {
                id: Date.now().toString(),
                title: taskText,
                completed: false
            };
            
            createTaskElement(task);
            
            const tasks = getTasksFromStorage();
            tasks.push(task);
            sessionStorage.setItem('tasks', JSON.stringify(tasks));
            
            taskEmptyState.style.display = "none";
            taskInput.value = "";
        }
    }
    
    function loadTasks() {
        const tasks = getTasksFromStorage();
        
        taskList.innerHTML = "";
        
        if (tasks.length === 0) {
            taskEmptyState.style.display = "block";
        } else {
            taskEmptyState.style.display = "none";
            
            tasks.forEach(task => {
                createTaskElement(task);
            });
        }
    }
    
    function createTaskElement(task) {
        const li = document.createElement("li");
        li.className = "task-item";
        li.dataset.id = task.id;
        
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "task-checkbox";
        checkbox.checked = task.completed || false;
        
        const taskText = document.createElement("span");
        taskText.className = "task-text";
        taskText.textContent = task.title;
        
        if (task.completed) {
            taskText.classList.add("completed");
        }
        
        
        checkbox.addEventListener("change", function() {
            updateTaskStatus(task.id, checkbox.checked);
            taskText.classList.toggle("completed", checkbox.checked);
        });
        
        li.appendChild(checkbox);
        li.appendChild(taskText);
        
        taskList.appendChild(li);
    }
    
    function updateTaskStatus(taskId, completed) {
        const tasks = getTasksFromStorage();
        const taskIndex = tasks.findIndex(task => task.id === taskId);
        
        if (taskIndex !== -1) {
            tasks[taskIndex].completed = completed;
            sessionStorage.setItem('tasks', JSON.stringify(tasks));
        }
    }
    
    function clearCompletedTasks() {
        const tasks = getTasksFromStorage();
        const remainingTasks = tasks.filter(task => !task.completed);
        
        sessionStorage.setItem('tasks', JSON.stringify(remainingTasks));
        
        loadTasks();
    }
    
    function getTasksFromStorage() {
        const tasksJson = sessionStorage.getItem('tasks');
        return tasksJson ? JSON.parse(tasksJson) : [];
    }
    
    // Pomodoro Timer Functionality 
    const timerDisplay = document.getElementById("timer");
    const timerStatus = document.getElementById("timer-status");
    const startButton = document.getElementById("start-timer");
    const pauseButton = document.getElementById("pause-timer");
    const resetButton = document.getElementById("reset-timer");
    const pomodoroButton = document.getElementById("pomodoro");
    const shortBreakButton = document.getElementById("short-break");
    const longBreakButton = document.getElementById("long-break");
    const soundToggle = document.getElementById("sound-toggle");
    const autoStartBreaks = document.getElementById("auto-start-breaks");
    
    // Timer settings
    const POMODORO_TIME = 25 * 60;
    const SHORT_BREAK_TIME = 5 * 60;
    const LONG_BREAK_TIME = 15 * 60;
    
    let timerInterval = null;
    let secondsLeft = POMODORO_TIME;
    let isRunning = false;
    let currentMode = "pomodoro";
    
    // Timer controls
    startButton.addEventListener("click", startTimer);
    pauseButton.addEventListener("click", pauseTimer);
    resetButton.addEventListener("click", resetTimer);
    
    // Timer mode buttons
    pomodoroButton.addEventListener("click", function() {
        setTimerMode("pomodoro");
    });
    
    shortBreakButton.addEventListener("click", function() {
        setTimerMode("shortBreak");
    });
    
    longBreakButton.addEventListener("click", function() {
        setTimerMode("longBreak");
    });
    
    function startTimer() {
        if (isRunning) return;
        
        isRunning = true;
        startButton.disabled = true;
        pauseButton.disabled = false;
        
        timerStatus.textContent = currentMode === "pomodoro" ? "Focus time!" : "Take a break!";
        
        timerInterval = setInterval(function() {
            if (secondsLeft > 0) {
                secondsLeft--;
                updateTimerDisplay();
            } else {
                timerComplete();
            }
        }, 1000);
    }
    
    function pauseTimer() {
        if (!isRunning) return;
        
        isRunning = false;
        clearInterval(timerInterval);
        timerInterval = null;
        startButton.disabled = false;
        pauseButton.disabled = true;
        timerStatus.textContent = "Paused";
    }
    
    function resetTimer() {
        isRunning = false;
        clearInterval(timerInterval);
        timerInterval = null;
        
        // Reset time based on current mode
        if (currentMode === "pomodoro") {
            secondsLeft = POMODORO_TIME;
        } else if (currentMode === "shortBreak") {
            secondsLeft = SHORT_BREAK_TIME;
        } else {
            secondsLeft = LONG_BREAK_TIME;
        }
        
        updateTimerDisplay();
        timerStatus.textContent = "Ready to focus";
        startButton.disabled = false;
        pauseButton.disabled = true;
    }
    
    function setTimerMode(mode) {
        // Only change if timer is not running
        if (isRunning) return;
        
        currentMode = mode;
        
        // Update active button
        pomodoroButton.classList.toggle("active", mode === "pomodoro");
        shortBreakButton.classList.toggle("active", mode === "shortBreak");
        longBreakButton.classList.toggle("active", mode === "longBreak");
        
        // Set appropriate time
        if (mode === "pomodoro") {
            secondsLeft = POMODORO_TIME;
            timerStatus.textContent = "Ready to focus";
        } else if (mode === "shortBreak") {
            secondsLeft = SHORT_BREAK_TIME;
            timerStatus.textContent = "Short break time";
        } else {
            secondsLeft = LONG_BREAK_TIME;
            timerStatus.textContent = "Long break time";
        }
        
        updateTimerDisplay();
    }
    
    function timerComplete() {
        isRunning = false;
        clearInterval(timerInterval);
        timerInterval = null;
        
        // Play notification sound if enabled
        if (soundToggle.checked) {
            try {
                const audio = new Audio('/static/website_app/sounds/alarm.mp3');
                audio.play();
            } catch (error) {
                console.error("Error playing sound:", error);
            }
        }
        
        timerStatus.textContent = "Time's up!";
        startButton.disabled = false;
        pauseButton.disabled = true;
        
        // Auto-start next timer if enabled
        if (autoStartBreaks.checked) {
            if (currentMode === "pomodoro") {
                // After pomodoro, start a short break
                setTimerMode("shortBreak");
                startTimer();
            } else {
                // After a break, start a pomodoro
                setTimerMode("pomodoro");
                startTimer();
            }
        }
    }
    
    function updateTimerDisplay() {
        timerDisplay.textContent = formatTime(secondsLeft);
    }
    
    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
    }
    
    // Initialize timer display
    updateTimerDisplay();
});