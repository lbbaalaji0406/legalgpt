import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
import random

TRIPLES_PATH = os.path.join(os.path.dirname(__file__), "data", "legal_triples.json")
WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "data", "gnn_weights.pt")

class LegalGNNTrainer:
    """
    Trains the Relational Knowledge Graph Embeddings using Margin-Based Ranking Loss.
    Learns continuous geometric representations of Indian law sections and relations.
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
        self.positive_triples = []

        self._build_vocab()

        self.num_entities = len(self.entity2id)
        self.num_relations = len(self.relation2id)

        self.entity_embeddings = nn.Embedding(self.num_entities, self.embedding_dim)
        self.relation_embeddings = nn.Embedding(self.num_relations, self.embedding_dim)

        nn.init.xavier_uniform_(self.entity_embeddings.weight)
        nn.init.xavier_uniform_(self.relation_embeddings.weight)

        self.optimizer = optim.Adam(
            list(self.entity_embeddings.parameters()) + list(self.relation_embeddings.parameters()),
            lr=self.lr
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

            self.positive_triples.append((self.entity2id[h], self.relation2id[r], self.entity2id[t]))

    def generate_negative_triples(self, pos_triples):
        """Corrupts head or tail to create negative contrastive training pairs."""
        neg_triples = []
        for h, r, t in pos_triples:
            if random.random() < 0.5:
                # Corrupt tail
                corrupt_t = random.randint(0, self.num_entities - 1)
                neg_triples.append((h, r, corrupt_t))
            else:
                # Corrupt head
                corrupt_h = random.randint(0, self.num_entities - 1)
                neg_triples.append((corrupt_h, r, t))
        return neg_triples

    def compute_energy(self, heads, relations, tails):
        h_emb = self.entity_embeddings(heads)
        r_emb = self.relation_embeddings(relations)
        t_emb = self.entity_embeddings(tails)
        # TransE distance: ||h + r - t||_2
        return torch.norm(h_emb + r_emb - t_emb, p=2, dim=1)

    def train(self, epochs: int = 100):
        print(f"[GNN Trainer] Starting training for {epochs} epochs...")
        print(f"[GNN Trainer] Total Entities: {self.num_entities} | Total Relations: {self.num_relations} | Total Triples: {len(self.positive_triples)}")

        pos_tensor = torch.tensor(self.positive_triples, dtype=torch.long)
        pos_h, pos_r, pos_t = pos_tensor[:, 0], pos_tensor[:, 1], pos_tensor[:, 2]

        for epoch in range(1, epochs + 1):
            self.optimizer.zero_grad()
            
            neg_triples = self.generate_negative_triples(self.positive_triples)
            neg_tensor = torch.tensor(neg_triples, dtype=torch.long)
            neg_h, neg_r, neg_t = neg_tensor[:, 0], neg_tensor[:, 1], neg_tensor[:, 2]

            pos_dist = self.compute_energy(pos_h, pos_r, pos_t)
            neg_dist = self.compute_energy(neg_h, neg_r, neg_t)

            # Target is -1 because we want pos_dist < neg_dist
            target = torch.tensor([-1.0] * len(self.positive_triples))
            loss = self.criterion(pos_dist, neg_dist, target)

            loss.backward()
            self.optimizer.step()

            # Normalize entity embeddings to unit ball
            with torch.no_grad():
                self.entity_embeddings.weight.div_(torch.norm(self.entity_embeddings.weight, p=2, dim=1, keepdim=True))

            if epoch % 20 == 0 or epoch == 1:
                print(f"  Epoch [{epoch:3d}/{epochs}] — Loss: {loss.item():.4f}")

        # Save weights
        os.makedirs(os.path.dirname(WEIGHTS_PATH), exist_ok=True)
        torch.save({
            "entity_embeddings": self.entity_embeddings.state_dict(),
            "relation_embeddings": self.relation_embeddings.state_dict(),
            "entity2id": self.entity2id,
            "relation2id": self.relation2id,
            "embedding_dim": self.embedding_dim
        }, WEIGHTS_PATH)
        print(f"[GNN Trainer] [OK] Training complete. Weights saved to {WEIGHTS_PATH}!")

if __name__ == "__main__":
    trainer = LegalGNNTrainer(embedding_dim=64, margin=1.0, lr=0.02)
    trainer.train(epochs=100)
