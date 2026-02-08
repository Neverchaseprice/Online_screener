document.addEventListener('DOMContentLoaded', function() {
    // Кнопка "Выбрать все" для каждой категории
    const categoryHeaders = document.querySelectorAll('.asset-category h3');
    categoryHeaders.forEach(header => {
        const categoryDiv = header.parentElement;
        const checkboxes = categoryDiv.querySelectorAll('input[type="checkbox"]');
        
        // Добавляем кнопку "Выбрать все" в каждую категорию
        const selectAllBtn = document.createElement('button');
        selectAllBtn.className = 'select-all-btn';
        selectAllBtn.textContent = '✓ Выбрать все';
        selectAllBtn.style.cssText = `
            margin: 5px 0 10px 0;
            padding: 5px 10px;
            background: #e3f2fd;
            border: 1px solid #90caf9;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.85em;
            color: #1565c0;
            transition: all 0.2s;
        `;
        selectAllBtn.style.cssText += `
            &:hover {
                background: #bbdefb;
                border-color: #64b5f6;
            }
        `;
        
        selectAllBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            const allChecked = Array.from(checkboxes).every(cb => cb.checked);
            checkboxes.forEach(cb => cb.checked = !allChecked);
            selectAllBtn.textContent = allChecked ? '✓ Выбрать все' : '✗ Снять все';
        });
        
        header.insertAdjacentElement('afterend', selectAllBtn);
    });
    
    // Глобальная кнопка "Выбрать все активы"
    const controlPanel = document.querySelector('.control-panel');
    if (controlPanel) {
        const selectAllGlobal = document.createElement('button');
        selectAllGlobal.id = 'select-all-global';
        selectAllGlobal.textContent = '✓ Выбрать все активы';
        selectAllGlobal.style.cssText = `
            margin: 10px 0 20px 0;
            padding: 10px 20px;
            background: #e8f5e9;
            border: 2px solid #81c784;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            color: #2e7d32;
            transition: all 0.3s;
            width: 100%;
        `;
        selectAllGlobal.style.cssText += `
            &:hover {
                background: #c8e6c9;
                border-color: #4caf50;
                transform: scale(1.02);
            }
            &:active {
                transform: scale(0.98);
            }
        `;
        
        selectAllGlobal.addEventListener('click', function(e) {
            e.preventDefault();
            const allCheckboxes = document.querySelectorAll('input[name="selected_assets"]');
            const allChecked = Array.from(allCheckboxes).every(cb => cb.checked);
            allCheckboxes.forEach(cb => cb.checked = !allChecked);
            this.textContent = allChecked ? '✓ Выбрать все активы' : '✗ Снять все активы';
        });
        
        const formGroup = controlPanel.querySelector('.form-group');
        if (formGroup) {
            formGroup.insertAdjacentElement('beforebegin', selectAllGlobal);
        }
    }
    
    // Валидация формы перед отправкой
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const checked = document.querySelectorAll('input[name="selected_assets"]:checked');
            if (checked.length === 0) {
                e.preventDefault();
                alert('⚠️ Пожалуйста, выберите хотя бы один актив для анализа!');
                return false;
            }
            
            if (checked.length > 10) {
                if (!confirm(`Вы выбрали ${checked.length} активов. Генерация может занять 2-3 минуты. Продолжить?`)) {
                    e.preventDefault();
                    return false;
                }
            }
            
            // Показать индикатор загрузки
            const btn = document.querySelector('.btn-generate');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '⏳ Загрузка данных...';
                btn.style.opacity = '0.85';
            }
        });
    }
    
    // Плавная прокрутка к графикам после генерации
    if (document.querySelector('.charts-container')) {
        setTimeout(() => {
            window.scrollTo({
                top: document.querySelector('.charts-container').offsetTop - 20,
                behavior: 'smooth'
            });
        }, 300);
    }
    
    // Фильтрация активов по поиску (опционально)
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.placeholder = '🔍 Поиск актива...';
    searchInput.style.cssText = `
        width: 100%;
        padding: 10px 15px;
        margin-bottom: 15px;
        border: 2px solid #ddd;
        border-radius: 8px;
        font-size: 1em;
        transition: border-color 0.3s;
    `;
    searchInput.addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        const checkboxes = document.querySelectorAll('.asset-checkbox');
        
        checkboxes.forEach(cb => {
            const label = cb.querySelector('span').textContent.toLowerCase();
            cb.style.display = label.includes(searchTerm) ? 'flex' : 'none';
        });
    });
    
    const assetsGrid = document.querySelector('.assets-grid');
    if (assetsGrid && !document.getElementById('asset-search')) {
        searchInput.id = 'asset-search';
        assetsGrid.insertAdjacentElement('beforebegin', searchInput);
    }
    
    // Hotkeys для удобства
    document.addEventListener('keydown', function(e) {
        // Ctrl+Enter или Cmd+Enter для отправки формы
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const checked = document.querySelectorAll('input[name="selected_assets"]:checked');
            if (checked.length > 0) {
                document.querySelector('form').requestSubmit();
            }
        }
        
        // Escape для снятия всех чекбоксов
        if (e.key === 'Escape') {
            document.querySelectorAll('input[name="selected_assets"]').forEach(cb => cb.checked = false);
            document.querySelectorAll('.select-all-btn').forEach(btn => {
                btn.textContent = '✓ Выбрать все';
            });
            document.getElementById('select-all-global').textContent = '✓ Выбрать все активы';
        }
    });
    
    // Сохранение выбранных активов в localStorage для удобства
    const checkboxes = document.querySelectorAll('input[name="selected_assets"]');
    checkboxes.forEach(cb => {
        // Загружаем сохраненные значения при загрузке страницы
        const saved = localStorage.getItem(`asset_${cb.value}`);
        if (saved !== null) {
            cb.checked = saved === 'true';
        }
        
        // Сохраняем при изменении
        cb.addEventListener('change', function() {
            localStorage.setItem(`asset_${this.value}`, this.checked);
        });
    });
    
    // Кнопка очистки сохраненных настроек
    if (document.querySelector('.control-panel')) {
        const clearBtn = document.createElement('button');
        clearBtn.textContent = '🗑️ Очистить сохраненные настройки';
        clearBtn.style.cssText = `
            margin: 10px 0;
            padding: 8px 15px;
            background: #ffebee;
            border: 1px solid #ef9a9a;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
            color: #c62828;
        `;
        clearBtn.addEventListener('click', function() {
            if (confirm('Очистить все сохраненные настройки выбора активов?')) {
                Object.keys(localStorage).forEach(key => {
                    if (key.startsWith('asset_')) {
                        localStorage.removeItem(key);
                    }
                });
                location.reload();
            }
        });
        document.querySelector('.control-panel').appendChild(clearBtn);
    }
});