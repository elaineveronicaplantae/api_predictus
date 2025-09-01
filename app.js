document.addEventListener('DOMContentLoaded', (event) => {
    // Botão Imprimir
    const btnPrint = document.getElementById("btnPrint");
    if (btnPrint) {
        btnPrint.addEventListener('click', () => {
            window.print();
        });
    }

    // Auto-formatação do campo CPF/CNPJ
    const cpfCnpjInput = document.getElementById('cpf_cnpj');
    if (cpfCnpjInput) {
        cpfCnpjInput.addEventListener('blur', (event) => {
            let value = event.target.value.replace(/\D/g, ''); // Remove todos os não-dígitos
            if (value.length === 11) {
                value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
            } else if (value.length === 14) {
                value = value.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
            }
            event.target.value = value;
        });
    }

    const form = document.getElementById("formImport");
    if (!form) return;

    const btn = document.getElementById("btnImportar");
    const divRes = document.getElementById("resultado");
    const divErro = document.getElementById("erro");
    const resumoDiv = document.getElementById("resumo");
    
    // Tabelas
    const tabelaResumo = document.getElementById("tabela-resumo");
    const tbodyResumo = document.querySelector("#tabela-resumo tbody");
    const tituloResumo = document.getElementById("resumo-titulo");
    const tabelaAchados = document.getElementById("tabela");
    const tbodyAchados = document.querySelector("#tabela tbody");
    
    // Modal
    const modal = document.getElementById("modalDetalhes");
    const closeModalButton = document.querySelector(".close-button");
    let achadosData = [];

    // Funções auxiliares RESTAURADAS
    function riscoBadge(r) {
      const riscoNormalizado = (r || "").toString().toLowerCase();
      const cls = riscoNormalizado === "vermelho" ? "vermelho" : riscoNormalizado === "laranja" ? "laranja" : "amarelo";
      return `<span class="badge ${cls}">${r || ""}</span>`;
    }

    function formatarMoeda(valor) {
      const numero = Number(valor) || 0;
      return numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    function abrirModal(processo) {
      document.getElementById('det-ramo').textContent = processo['Ramo do Direito'] || '';
      document.getElementById('det-classe').textContent = processo['Classe Processual'] || '';
      document.getElementById('det-instancia').textContent = processo['Instância'] || '';
      document.getElementById('det-distribuicao').textContent = processo['Data de Distribuição'] || '';
      document.getElementById('det-status').textContent = processo['Status'] || '';
      document.getElementById('det-valor').textContent = formatarMoeda(processo['Valor da Causa']);
      document.getElementById('det-tutela').textContent = processo['Tutela Antecipada'] || '';
      document.getElementById('det-outras-partes').textContent = processo['Outras Partes'] || '';
      document.getElementById('det-julgamentos').textContent = processo['Julgamentos'] || '';
      document.getElementById('det-mov1').textContent = processo['1ª Movimentação'] || '';
      document.getElementById('det-mov2').textContent = processo['2ª Movimentação'] || '';
      document.getElementById('det-mov3').textContent = processo['3ª Movimentação'] || '';
      document.getElementById('det-atualizacao').textContent = processo['Data de Atualização'] || '';
      modal.style.display = 'flex';
    }
    closeModalButton.onclick = () => { modal.style.display = 'none'; };
    window.onclick = (event) => { if (event.target == modal) { modal.style.display = 'none'; } };
    tbodyAchados.addEventListener('click', (event) => {
        const tr = event.target.closest('tr');
        if (!tr) return;
        const rowIndex = tr.rowIndex - 1;
        const processoClicado = achadosData[rowIndex];
        if (processoClicado) { abrirModal(processoClicado); }
    });

    // Lógica principal do formulário
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      divErro.classList.add("hidden");
      divRes.classList.add("hidden");
      btn.disabled = true;
      achadosData = [];

      const data = new FormData(form);
      try {
        const respImport = await fetch("/importar", { method: "POST", body: data });
        const jsonImport = await respImport.json();
        if (!respImport.ok) throw new Error(jsonImport.erro || "Falha ao importar");

        const cpf_cnpj = data.get('cpf_cnpj');
        const respAchados = await fetch(`/achados?cpf_cnpj=${cpf_cnpj}`);
        const jsonAchados = await respAchados.json();
        if (!respAchados.ok) throw new Error(jsonAchados.erro || "Falha ao buscar achados.");
        
        // Lógica de exibição do resumo RESTAURADA
        resumoDiv.innerHTML = ''; 
        const totalGeral = document.createElement('p');
        totalGeral.textContent = `${jsonAchados.total || 0} processos encontrados.`;
        resumoDiv.appendChild(totalGeral);

        tbodyResumo.innerHTML = '';
        const resumoData = jsonAchados.resumo || [];
        if (resumoData.length > 0) {
          tituloResumo.classList.remove("hidden");
          tabelaResumo.classList.remove("hidden");
          let ultimaClasseProcessual = '';
          resumoData.forEach(item => {
              const tr = document.createElement('tr');
              let classeProcessualCell = `<td>${item['Classe Processual']}</td>`;
              if (item['Classe Processual'] === ultimaClasseProcessual) {
                  classeProcessualCell = '<td></td>';
              }
              tr.innerHTML = `
                  ${classeProcessualCell}
                  <td>${item['Status']}</td>
                  <td>${item.quantidade}</td>
                  <td>${formatarMoeda(item.valor_total)}</td>
              `;
              tbodyResumo.appendChild(tr);
              ultimaClasseProcessual = item['Classe Processual'];
          });
        } else {
            tituloResumo.classList.add("hidden");
            tabelaResumo.classList.add("hidden");
        }
        
        // Lógica de exibição dos achados ATUALIZADA (sem Risco/Score)
        tbodyAchados.innerHTML = "";
        achadosData = jsonAchados.achados || [];
        if (achadosData.length > 0) {
          achadosData.forEach(proc => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
              <td>${proc['N° Processo'] || ''}</td>
              <td>${proc['Partes Ativas'] || ''}</td>
              <td>${proc['Partes Passivas'] || ''}</td>
              <td>${proc['Classe Processual'] || ''}</td>
              <td>${formatarMoeda(proc['Valor da Causa'])}</td>
            `;
            tbodyAchados.appendChild(tr);
          });
        }
        divRes.classList.remove("hidden");
      } catch (err) {
        divErro.textContent = err.message;
        divErro.classList.remove("hidden");
      } finally {
        btn.disabled = false;
      }
    });
});
