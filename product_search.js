/**
 * product_search.js - Funções para busca inteligente de produtos no catálogo
 * 
 * Este arquivo contém as funções necessárias para realizar buscas no catálogo
 * de produtos, com filtros por aplicação de veículos, facilitando a criação
 * de orçamentos pelo mecânico.
 */

// Configuração inicial
const API_BASE_URL = '/api';

/**
 * Realiza busca de produtos com base nos parâmetros fornecidos
 * @param {Object} params - Parâmetros de busca
 * @param {Function} callback - Função de callback para processar resultados
 */
function searchProducts(params, callback) {
    // Parâmetros padrão
    const defaultParams = {
        search: '',
        vehicle_brand: '',
        vehicle_model: '',
        vehicle_year: '',
        page: 1,
        per_page: 20
    };

    // Mesclar parâmetros fornecidos com os padrões
    const queryParams = { ...defaultParams, ...params };
    
    // Construir string de consulta
    const queryString = Object.keys(queryParams)
        .filter(key => queryParams[key] !== '')
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(queryParams[key])}`)
        .join('&');

    // Realizar requisição AJAX
    fetch(`${API_BASE_URL}/mechanic/products_for_quote?${queryString}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro na busca de produtos');
            }
            return response.json();
        })
        .then(data => {
            if (typeof callback === 'function') {
                callback(null, data);
            }
        })
        .catch(error => {
            console.error('Erro ao buscar produtos:', error);
            if (typeof callback === 'function') {
                callback(error, null);
            }
        });
}

/**
 * Carrega marcas de veículos para o seletor
 * @param {string} selectId - ID do elemento select para marcas
 * @param {Function} callback - Função de callback opcional
 */
function loadVehicleBrands(selectId, callback) {
    const selectElement = document.getElementById(selectId);
    
    if (!selectElement) {
        console.error(`Elemento com ID ${selectId} não encontrado`);
        return;
    }
    
    fetch(`${API_BASE_URL}/vehicle_brands`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao carregar marcas de veículos');
            }
            return response.json();
        })
        .then(brands => {
            // Limpar opções existentes
            selectElement.innerHTML = '<option value="">Selecione a marca</option>';
            
            // Adicionar novas opções
            brands.forEach(brand => {
                const option = document.createElement('option');
                option.value = brand.name;
                option.textContent = brand.name;
                option.dataset.brandId = brand.id;
                selectElement.appendChild(option);
            });
            
            if (typeof callback === 'function') {
                callback(null, brands);
            }
        })
        .catch(error => {
            console.error('Erro ao carregar marcas de veículos:', error);
            if (typeof callback === 'function') {
                callback(error, null);
            }
        });
}

/**
 * Carrega modelos de veículos para o seletor com base na marca selecionada
 * @param {string} brandSelectId - ID do elemento select para marcas
 * @param {string} modelSelectId - ID do elemento select para modelos
 */
function loadVehicleModels(brandSelectId, modelSelectId) {
    const brandSelect = document.getElementById(brandSelectId);
    const modelSelect = document.getElementById(modelSelectId);
    
    if (!brandSelect || !modelSelect) {
        console.error('Elementos de seleção não encontrados');
        return;
    }
    
    const selectedOption = brandSelect.options[brandSelect.selectedIndex];
    const brandId = selectedOption ? selectedOption.dataset.brandId : null;
    
    if (!brandId) {
        // Limpar modelos se nenhuma marca selecionada
        modelSelect.innerHTML = '<option value="">Selecione o modelo</option>';
        modelSelect.disabled = true;
        return;
    }
    
    // Habilitar select de modelos e mostrar carregando
    modelSelect.disabled = true;
    modelSelect.innerHTML = '<option value="">Carregando...</option>';
    
    fetch(`${API_BASE_URL}/vehicle_brands/${brandId}/models`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Erro ao carregar modelos de veículos');
            }
            return response.json();
        })
        .then(models => {
            // Limpar opções existentes
            modelSelect.innerHTML = '<option value="">Selecione o modelo</option>';
            
            // Adicionar novas opções
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.name;
                option.textContent = model.name;
                option.dataset.modelId = model.id;
                modelSelect.appendChild(option);
            });
            
            // Habilitar select de modelos
            modelSelect.disabled = false;
        })
        .catch(error => {
            console.error('Erro ao carregar modelos de veículos:', error);
            modelSelect.innerHTML = '<option value="">Erro ao carregar modelos</option>';
            modelSelect.disabled = true;
        });
}

/**
 * Adiciona produto ao orçamento atual
 * @param {number} productId - ID do produto a ser adicionado
 * @param {Object} productData - Dados do produto
 */
function addProductToQuote(productId, productData) {
    // Verificar se já existe um orçamento em andamento
    let currentQuote = JSON.parse(localStorage.getItem('currentQuote') || '{"items":[]}');
    
    // Verificar se o produto já está no orçamento
    const existingItemIndex = currentQuote.items.findIndex(item => item.productId === productId);
    
    if (existingItemIndex >= 0) {
        // Incrementar quantidade se já existir
        currentQuote.items[existingItemIndex].quantity += 1;
    } else {
        // Adicionar novo item
        currentQuote.items.push({
            productId: productId,
            code: productData.code,
            name: productData.name,
            price: productData.price,
            quantity: 1,
            subtotal: productData.price
        });
    }
    
    // Recalcular total
    currentQuote.total = currentQuote.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    
    // Salvar orçamento atualizado
    localStorage.setItem('currentQuote', JSON.stringify(currentQuote));
    
    // Disparar evento para notificar atualização
    const event = new CustomEvent('quoteUpdated', { detail: currentQuote });
    document.dispatchEvent(event);
    
    return currentQuote;
}

/**
 * Renderiza resultados da busca na tabela
 * @param {string} tableId - ID da tabela para exibir resultados
 * @param {Object} results - Resultados da busca
 */
function renderSearchResults(tableId, results) {
    const tableBody = document.querySelector(`#${tableId} tbody`);
    
    if (!tableBody) {
        console.error(`Elemento tbody dentro de #${tableId} não encontrado`);
        return;
    }
    
    // Limpar resultados anteriores
    tableBody.innerHTML = '';
    
    if (!results.products || results.products.length === 0) {
        // Exibir mensagem de nenhum resultado
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="5" class="text-center">Nenhum produto encontrado</td>';
        tableBody.appendChild(row);
        return;
    }
    
    // Adicionar produtos à tabela
    results.products.forEach(product => {
        const row = document.createElement('tr');
        
        // Formatar aplicações
        let applicationsHtml = '';
        if (product.applications_summary && product.applications_summary.length > 0) {
            applicationsHtml = product.applications_summary.join('<br>');
            if (product.has_more_applications) {
                applicationsHtml += '<br><small class="text-muted">E mais...</small>';
            }
        } else {
            applicationsHtml = '<small class="text-muted">Sem aplicações cadastradas</small>';
        }
        
        // Formatar disponibilidade
        const stockClass = product.stock > 0 ? 'text-success' : 'text-danger';
        const stockText = product.stock > 0 ? 'Em estoque' : 'Indisponível';
        
        // Construir HTML da linha
        row.innerHTML = `
            <td>${product.code}</td>
            <td>
                <strong>${product.name}</strong>
                <div class="small text-muted">${product.description || ''}</div>
                <div class="small">${product.manufacturer || ''}</div>
            </td>
            <td>${applicationsHtml}</td>
            <td class="text-right">R$ ${product.price.toFixed(2)}</td>
            <td>
                <span class="${stockClass}">${stockText}</span>
                <button class="btn btn-sm btn-primary add-to-quote" data-product-id="${product.id}">
                    <i class="fas fa-plus"></i> Adicionar
                </button>
            </td>
        `;
        
        // Adicionar evento ao botão
        const addButton = row.querySelector('.add-to-quote');
        if (addButton) {
            addButton.addEventListener('click', () => {
                addProductToQuote(product.id, product);
                
                // Feedback visual
                addButton.classList.remove('btn-primary');
                addButton.classList.add('btn-success');
                addButton.innerHTML = '<i class="fas fa-check"></i> Adicionado';
                
                setTimeout(() => {
                    addButton.classList.remove('btn-success');
                    addButton.classList.add('btn-primary');
                    addButton.innerHTML = '<i class="fas fa-plus"></i> Adicionar';
                }, 2000);
            });
        }
        
        tableBody.appendChild(row);
    });
    
    // Adicionar paginação se necessário
    if (results.pages > 1) {
        const paginationContainer = document.createElement('div');
        paginationContainer.className = 'pagination-container mt-3';
        
        const pagination = document.createElement('ul');
        pagination.className = 'pagination justify-content-center';
        
        // Botão anterior
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${results.page <= 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `<a class="page-link" href="#" data-page="${results.page - 1}">Anterior</a>`;
        pagination.appendChild(prevLi);
        
        // Páginas
        const maxPages = Math.min(5, results.pages);
        let startPage = Math.max(1, results.page - 2);
        let endPage = Math.min(results.pages, startPage + maxPages - 1);
        
        if (endPage - startPage < maxPages - 1) {
            startPage = Math.max(1, endPage - maxPages + 1);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const pageLi = document.createElement('li');
            pageLi.className = `page-item ${i === results.page ? 'active' : ''}`;
            pageLi.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i}</a>`;
            pagination.appendChild(pageLi);
        }
        
        // Botão próximo
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${results.page >= results.pages ? 'disabled' : ''}`;
        nextLi.innerHTML = `<a class="page-link" href="#" data-page="${results.page + 1}">Próximo</a>`;
        pagination.appendChild(nextLi);
        
        paginationContainer.appendChild(pagination);
        tableBody.parentNode.parentNode.appendChild(paginationContainer);
        
        // Adicionar eventos aos links de paginação
        paginationContainer.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(link.dataset.page);
                
                if (page && page !== results.page) {
                    // Obter parâmetros atuais
                    const searchInput = document.getElementById('product-search');
                    const brandSelect = document.getElementById('vehicle-brand');
                    const modelSelect = document.getElementById('vehicle-model');
                    const yearInput = document.getElementById('vehicle-year');
                    
                    // Realizar nova busca com a página selecionada
                    searchProducts({
                        search: searchInput ? searchInput.value : '',
                        vehicle_brand: brandSelect ? brandSelect.value : '',
                        vehicle_model: modelSelect ? modelSelect.value : '',
                        vehicle_year: yearInput ? yearInput.value : '',
                        page: page,
                        per_page: results.per_page
                    }, (err, newResults) => {
                        if (!err) {
                            renderSearchResults(tableId, newResults);
                        }
                    });
                }
            });
        });
    }
}

// Exportar funções para uso global
window.catalogSearch = {
    searchProducts,
    loadVehicleBrands,
    loadVehicleModels,
    addProductToQuote,
    renderSearchResults
};
