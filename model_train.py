import PIL.Image
import cv2
import numpy as np
import os
import csv
from PIL import Image
import torch
import torchvision.transforms as transforms
from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split
import random
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision.models.segmentation.deeplabv3 import DeepLabHead
from torchvision.models.segmentation.deeplabv3 import deeplabv3_resnet50,DeepLabV3_ResNet50_Weights



from torchvision import models
from sklearn.metrics import average_precision_score

from torchvision.models.segmentation import fcn_resnet50,FCN_ResNet50_Weights

from PIL import Image, ImageDraw
import numpy as np
import xml.etree.ElementTree as et
import matplotlib.pyplot as plts
class ImageSegmentationDataset(torch.utils.data.Dataset):
    def __init__(self,img_path,annot_path,mask_path,transforms):
        self.transform = transforms
        self.img_path = img_path
        self.annotations_path = annot_path
        self.masks_path = mask_path

        self.img_list = []
        self.annotations_list = []
        self.masks_list = []
        for img in os.listdir(img_path):
            self.img_list.append(os.path.join(img_path,img))
        for annot in os.listdir(self.annotations_path):
            self.annotations_list.append(os.path.join(annot_path, annot))
    def generate_masks(self):
        # print(self.annotations_path)
        if(os.listdir(self.masks_path) == []):
            annot_path = self.annotations_path
            for annot in os.listdir(annot_path):
                # Randomly appearing desktop.ini, need to skip
                if(annot == "desktop.ini"):
                    pass
                else:
                    print(os.path.join(annot_path, annot))
                    tree = et.parse(os.path.join(annot_path,annot))
                    root = tree.getroot()
                    maskes = []
                    img_size = (1000,1000)
                    # Create empty image
                    masked_image = Image.new("LA",img_size,color=(0,0))
                    # Get the Mask of the images
                    for region in root.findall(".//Region"):
                        vertices = region.findall(".//Vertex")
                        mask = [(float(vertex.get("X")), float(vertex.get("Y"))) for vertex in vertices]
                        maskes.append(mask)
                    # Generate Mask for each image from the annotations
                    #
                    print(self.masks_path)
                    for mask in maskes:
                        draw = ImageDraw.Draw(masked_image)
                        draw.polygon(mask,fill=(255,255))
                    image_array = np.array(masked_image)
                    masked_image.save(f'{self.masks_path}\\{annot[:-4]}.png')
                    self.masks_list.append(f'{self.masks_path}\\{annot[:-4]}.png')
                    # self.masks_list.append(maskes)
        else:
            mask_path = self.masks_path
            # print(mask_path)
            for mask in os.listdir(mask_path):
                self.masks_list.append(os.path.join(mask_path,mask))
    def __len__(self):
        return  len(self.img_list)

    def __getitem__(self,idx):
        img_path = self.img_list[idx]
        maskes = self.masks_list[idx]
        # print(maskes)
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # img = img.transpose(2,0,1)
        mask = cv2.imread(maskes)
        mask = cv2.cvtColor(mask,cv2.COLOR_BGR2GRAY)

        # img = Image.open(img_path).convert('RGB')
        # maskes = cv2.imread(maskes)
        mask[mask<=0] = 0
        mask[mask>=1] = 1
        img = Image.fromarray(img)
        mask = Image.fromarray(mask)
        if(self.transform is not None):
            # print(self.transform)
            img = self.transform(img)
            mask = self.transform(mask)

        return img,mask

trg_transforms1 = (transforms.Compose
([
    transforms.Resize(64),
    transforms.RandomCrop(64),
    transforms.ToTensor(),
    # transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
]))

val_transforms1 = (transforms.Compose
([
    transforms.Resize(64),
    transforms.CenterCrop(64),
    transforms.ToTensor(),
    # transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
]))
def train_model(model,train_loader,criterion,optimizer,device):
    model.train()
    data_size = 0
    avg_loss = 0
    for images,masks in train_loader:
        images,masks = images.to(device),masks.to(device)
        # print(len(images))
        # print(type(images))
        # print(type(masks))

        outputs = model(images)
        out_tensor = outputs['out']
        # aux_tensor = outputs['aux']
        #
        print(masks.shape)
        print(out_tensor.shape)

        # print(images)
        # print(masks)
        loss = criterion(out_tensor,masks)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        avg_loss = (avg_loss * data_size + loss) / (data_size + images.shape[0])
        data_size += images.shape[0]
    return avg_loss


def generate_datasets(train_root,val_root,trg_transforms,val_transforms):
    train_img_path = os.path.join(train_root,"tissue_image")
    train_annot_path = os.path.join(train_root,"annotations")
    train_mask_path = os.path.join(train_root,"masks")
    val_img_path = os.path.join(val_root,"tissue_image")
    val_annot_path = os.path.join(val_root,"annotations")
    val_mask_path = os.path.join(val_root,"masks")
    train_dataset = ImageSegmentationDataset(train_img_path,train_annot_path,train_mask_path,trg_transforms)
    train_dataset.generate_masks()
    val_dataset = ImageSegmentationDataset(val_img_path, val_annot_path, val_mask_path, val_transforms)
    val_dataset.generate_masks()
    return train_dataset,val_dataset

if __name__ == "__main__":
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    train_root = "MonuSegTrainData"
    val_root = "MonuSegTestData"
    model = deeplabv3_resnet50(weights = DeepLabV3_ResNet50_Weights.DEFAULT)

    # train_img_path = "MonuSeg_Train\\tissue_image"
    # annot_path = "MoNuSeg_Train\\annotations"
    # mask_path = "MoNuSeg_Train\\masks"
    train_dataset,val_dataset = generate_datasets(train_root,val_root,trg_transforms1,val_transforms1)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False, num_workers=4)
    dataloaders = \
        {
            "train": train_loader,
            "val": val_loader
        }
    # lr_list = [0.001,0.01,0.1]
    lr_list = [0.001]
    # print(model.classifier[1].num_features)
    for lr in lr_list:
        model.classifier = DeepLabHead(2048,1)
        # model.classifier[1] = torch.nn.Linear(model.classifier[1].num_features,2)
        model.to(device)
        optimizer = optim.RMSprop(model.parameters(), lr=lr)
        # loss_crit = torch.nn.CrossEntropyLoss(weight=None, size_average=None, ignore_index=-100,
        #                                       reduce=None, reduction='mean')
        loss_crit = torch.nn.BCEWithLogitsLoss(reduction='mean')
        best_hyperparameter = None
        weights_chosen = None
        bestmeasure = None
        avg_loss = train_model(model,dataloaders['train'],loss_crit,optimizer,device)
        print(avg_loss.item())







