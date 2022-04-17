import torch
import random
from torch import nn
import numpy as np
import torch.nn.functional as F
import utils


class ADACL(nn.Module):

    def __init__(self, in_channel=1, num_classes=3, num_source=1):
        super(ADACL, self).__init__()

        self.num_source = num_source
        self.feature_extractor = nn.Sequential(
            nn.Conv1d(in_channel, 4, kernel_size=9, padding=1),
            nn.BatchNorm1d(4),
            nn.ReLU(inplace=True),
            nn.Maxpool1d(kernel_size=2, stride=2),

            nn.Conv1d(4, 8, kernel_size=9, padding=1),
            nn.BatchNorm1d(8),
            nn.ReLU(inplace=True),
            nn.Maxpool1d(kernel_size=2, stride=2),

            nn.Conv1d(8, 16, kernel_size=9, padding=1),
            nn.BatchNorm1d(16),
            nn.ReLU(inplace=True),
            nn.Maxpool1d(kernel_size=2, stride=2),

            nn.Conv1d(16, 32, kernel_size=9, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),
            nn.Maxpool1d(kernel_size=2, stride=2),

            nn.Conv1d(32, 64, kernel_size=9, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.Maxpool1d(kernel_size=2, stride=2),

            nn.Conv1d(64, 128, kernel_size=9, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveMaxPool1d(4),

            nn.Flatten(),
            nn.Linear(4*128, 256),
            nn.ReLU(inplace=True),

            nn.Linear(256, 128),
            nn.ReLU(inplace=True))

        self.clf = nn.ModuleList([nn.Linear(128, num_classes) \
                                              for _ in range(num_source)])

        self.discriminator = nn.Sequential(
            nn.Linear(128, 10),
            nn.ReLU(inplace=True),
            nn.Linear(10, int(1+num_source)))
 
        self.grl = utils.GradientReverseLayer()

    def forward(self, source_data, target_data, source_label, source_idx):
        batch_size = source_data.shape[0]
        feat_src = self.feature_extractor(source_data)
        feat_tgt = self.feature_extractor(target_data)

        logits = [cl(feat_src) for cl in self.cls]
        loss_cls = F.nll_loss(F.log_softmax(logits[source_idx], dim=1), source_label)
       
        labels_dm = torch.concat((torch.full(batch_size, source_idx, dtype=torch.int32),
                                    torch.zeros(batch_size, dtype=torch.int32)), dim=0)
        feat = self.grl(torch.concat((feat_src, feat_tgt), dim=0))
        logits_dm = self.discriminator(feat)
        loss_d = F.nll_loss(F.log_softmax(logits_dm, dim=1), labels_dm)
        
        logits = [F.softmax(data, dim=1) for data in logits]
        loss_l1 = 0.0
        for i in range(len(logits)):
            for j in range(len(logits)):
                loss_l1 += torch.abs(logits[i] - logits[j]).sum()
        loss_l1 /= 2*self.num_source

        loss_total = loss_cls + loss_d + loss_l1

        return loss_total


if __name__ == '__main__':
    x = torch.randn((32, 1, 1024))
    tar = torch.randn((32, 1, 1024))
    label = torch.randint(3, (32,))
    model = ADACL()
    loss = model(x, tar, label, 1) 
    print(loss)