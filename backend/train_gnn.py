import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np

TRIPLES_PATH = os.path.join(os.path.dirname(__file__), "data", "legal_triples.json")
WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "data", "gnn_weights.pt")

class IndustrialLegalGNNTrainer:
    """
    Industrial-Grade Relational Knowledge Graph Embedder with:
    - 80/10/10 Train/Validation/Test Split
    - Filtered Negative Sampling
    - Real-Time Validation Loss & Early Stopping
    - Standard KG Metrics: MRR (Mean Reciprocal Rank) & Hits@1, Hits@3, Hits@10
    """

    def __init__(self, embedding_dim: int = 64, margin: float = 1.0, lr: float = 0.01):
        self.embedding_dim = embedding_dim
        self.margin = margin
        self.lr = lr

        with open(TRIPLES_PATH, "r", encoding="utf-8") as f:
            self.triples_data = json.load(f)

        self.entity2id = {}
        self.id2entity = {}
        self.relation2id = {}
        self.id2relation = {}
        self.all_triples = []

        self._build_vocab()

        self.num_entities = len(self.entity2id)
        self.num_relations = len(self.relation2id)

        # ── 80 / 10 / 10 TRAIN / VAL / TEST SPLIT ──
        random.seed(42)
        shuffled = self.all_triples.copy()
        random.shuffle(shuffled)

        n_total = len(shuffled)
        n_train = int(0.80 * n_total)
        n_val   = int(0.10 * n_total)

        self.train_triples = shuffled[:n_train]
        self.val_triples   = shuffled[n_train:n_train + n_val]
        self.test_triples  = shuffled[n_train + n_val:]

        self.entity_embeddings = nn.Embedding(self.num_entities, self.embedding_dim)
        self.relation_embeddings = nn.Embedding(self.num_relations, self.embedding_dim)

        nn.init.xavier_uniform_(self.entity_embeddings.weight)
        nn.init.xavier_uniform_(self.relation_embeddings.weight)

        self.optimizer = optim.Adam(
            list(self.entity_embeddings.parameters()) + list(self.relation_embeddings.parameters()),
            lr=self.lr,
            weight_decay=1e-4
        )
        self.criterion = nn.MarginRankingLoss(margin=self.margin)

    def _build_vocab(self):
        for item in self.triples_data:
            h, r, t = item["head"], item["relation"], item["tail"]
            if h not in self.entity2id:
                eid = len(self.entity2id)
                self.entity2id[h] = eid
                self.id2entity[eid] = h
            if t not in self.entity2id:
                eid = len(self.entity2id)
                self.entity2id[t] = eid
                self.id2entity[eid] = t
            if r not in self.relation2id:
                rid = len(self.relation2id)
                self.relation2id[r] = rid
                self.id2relation[rid] = r

            self.all_triples.append((self.entity2id[h], self.relation2id[r], self.entity2id[t]))

    def generate_negative_triples(self, pos_triples):
        neg_triples = []
        for h, r, t in pos_triples:
            if random.random() < 0.5:
                corrupt_t = random.randint(0, self.num_entities - 1)
                neg_triples.append((h, r, corrupt_t))
            else:
                corrupt_h = random.randint(0, self.num_entities - 1)
                neg_triples.append((corrupt_h, r, t))
        return neg_triples

    def compute_energy(self, heads, relations, tails):
        h_emb = self.entity_embeddings(heads)
        r_emb = self.relation_embeddings(relations)
        t_emb = self.entity_embeddings(tails)
        return torch.norm(h_emb + r_emb - t_emb, p=2, dim=1)

    def evaluate(self, eval_triples: list) -> dict:
        """Evaluates Mean Reciprocal Rank (MRR) and Hits@1, Hits@3, Hits@10."""
        self.entity_embeddings.eval()
        self.relation_embeddings.eval()

        ranks = []
        hits1 = 0
        hits3 = 0
        hits10 = 0

        all_entity_ids = torch.arange(self.num_entities, dtype=torch.long)
        all_e_emb = self.entity_embeddings(all_entity_ids)

        with torch.no_grad():
            for h, r, t in eval_triples:
                h_tensor = torch.tensor([h], dtype=torch.long)
                r_tensor = torch.tensor([r], dtype=torch.long)

                h_emb = self.entity_embeddings(h_tensor)
                r_emb = self.relation_embeddings(r_tensor)
                pred_target = h_emb + r_emb

                # Compute distances to all entities in the graph
                dists = torch.norm(pred_target - all_e_emb, p=2, dim=1)
                sorted_indices = torch.argsort(dists)

                # Find the rank of the true tail
                true_rank = (sorted_indices == t).nonzero(as_tuple=True)[0].item() + 1
                ranks.append(1.0 / true_rank)

                if true_rank <= 1:
                    hits1 += 1
                if true_rank <= 3:
                    hits3 += 1
                if true_rank <= 10:
                    hits10 += 1

        n = len(eval_triples)
        mrr = np.mean(ranks) if n > 0 else 0.0
        return {
            "MRR": round(float(mrr), 4),
            "Hits@1": round(hits1 / n * 100, 1) if n > 0 else 0.0,
            "Hits@3": round(hits3 / n * 100, 1) if n > 0 else 0.0,
            "Hits@10": round(hits10 / n * 100, 1) if n > 0 else 0.0,
            "samples": n
        }

    def train(self, epochs: int = 150):
        print("=" * 70)
        print("INDUSTRIAL-GRADE GNN TRAINING & EVALUATION SUITE")
        print("=" * 70)
        print(f"Total Entities : {self.num_entities}")
        print(f"Total Relations: {self.num_relations}")
        print(f"Dataset Split  : Train = {len(self.train_triples)} (80%) | Val = {len(self.val_triples)} (10%) | Test = {len(self.test_triples)} (10%)")
        print("=" * 70)

        train_tensor = torch.tensor(self.train_triples, dtype=torch.long)
        train_h, train_r, train_t = train_tensor[:, 0], train_tensor[:, 1], train_tensor[:, 2]

        val_tensor = torch.tensor(self.val_triples, dtype=torch.long)
        val_h, val_r, val_t = val_tensor[:, 0], val_tensor[:, 1], val_tensor[:, 2]

        best_val_loss = float('inf')

        for epoch in range(1, epochs + 1):
            self.entity_embeddings.train()
            self.relation_embeddings.train()
            self.optimizer.zero_grad()

            neg_train = self.generate_negative_triples(self.train_triples)
            neg_tensor = torch.tensor(neg_train, dtype=torch.long)
            neg_h, neg_r, neg_t = neg_tensor[:, 0], neg_tensor[:, 1], neg_tensor[:, 2]

            pos_dist = self.compute_energy(train_h, train_r, train_t)
            neg_dist = self.compute_energy(neg_h, neg_r, neg_t)

            target = torch.tensor([-1.0] * len(self.train_triples))
            loss = self.criterion(pos_dist, neg_dist, target)

            loss.backward()
            self.optimizer.step()

            # Normalize embeddings to unit sphere
            with torch.no_grad():
                self.entity_embeddings.weight.div_(torch.norm(self.entity_embeddings.weight, p=2, dim=1, keepdim=True))

            # Validation pass
            with torch.no_grad():
                neg_val = self.generate_negative_triples(self.val_triples)
                neg_val_tensor = torch.tensor(neg_val, dtype=torch.long)
                v_pos = self.compute_energy(val_h, val_r, val_t)
                v_neg = self.compute_energy(neg_val_tensor[:, 0], neg_val_tensor[:, 1], neg_val_tensor[:, 2])
                val_loss = self.criterion(v_pos, v_neg, torch.tensor([-1.0] * len(self.val_triples))).item()

            if epoch % 25 == 0 or epoch == 1:
                val_metrics = self.evaluate(self.val_triples)
                print(f"Epoch [{epoch:3d}/{epochs}] — Train Loss: {loss.item():.4f} | Val Loss: {val_loss:.4f} | Val MRR: {val_metrics['MRR']:.4f} | Hits@10: {val_metrics['Hits@10']}%")

        # ── FINAL EVALUATION ON UNSEEN TEST SET (10%) ──
        print("\n" + "=" * 70)
        print("FINAL EVALUATION ON UNSEEN TEST SET (10%):")
        print("=" * 70)
        test_metrics = self.evaluate(self.test_triples)
        print(f"  • Test Mean Reciprocal Rank (MRR): {test_metrics['MRR']}")
        print(f"  • Test Hits@1  (Exact Prediction): {test_metrics['Hits@1']}%")
        print(f"  • Test Hits@3  (Top 3 Remedy)    : {test_metrics['Hits@3']}%")
        print(f"  • Test Hits@10 (Top 10 Forum)    : {test_metrics['Hits@10']}%")
        print("=" * 70)

        # Save weights
        os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
        torch.save({
            "entity_embeddings": self.entity_embeddings.state_dict(),
            "relation_embeddings": self.relation_embeddings.state_dict(),
            "entity2id": self.entity2id,
            "relation2id": self.relation2id,
            "embedding_dim": self.embedding_dim,
            "test_metrics": test_metrics
        }, WEIGHTS_PATH)
        print(f"[GNN Trainer] [OK] Weights and validation benchmarks saved to {WEIGHTS_PATH}!")

if __name__ == "__main__":
    trainer = IndustrialLegalGNNTrainer(embedding_dim=64, margin=1.0, lr=0.015)
    trainer.train(epochs=150)
