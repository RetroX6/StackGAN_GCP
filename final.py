#!/usr/bin/env python
# coding: utf-8

# In[55]:

import streamlit as st
import torch
from torchvision import transforms
import numpy as np
import pandas as pd
from PIL import Image
import os
from torchvision.utils import make_grid
import matplotlib.image as mpimg
 
import random
import argparse

import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import pickle
import torch.utils.data as data

import warnings
warnings.filterwarnings("ignore") 

############################################################################################################################################

st.set_page_config(page_title='StackGAN On Birds Dataset')

st.title('Generating Images: StackGAN Implementation', anchor=None)

image = Image.open('dataset-cover.jpg')
st.image(image, caption='Birds Dataset')

padding = 0
st.markdown(f""" <style>
    .reportview-container .main .block-container{{
        padding-top: {padding}rem;
        padding-right: {padding}rem;
        padding-left: {padding}rem;
        padding-bottom: {padding}rem;
    }} </style> """, unsafe_allow_html=True)

st.header('Objective')

st.write('Synthesizing photo-realistic images from text descriptions is a challenging problem in computer vision and has many practical applications. Samples generated by existing text-to-image approaches can roughly reflect the meaning of the given descriptions, but they fail to contain necessary details and vivid object parts. This complex problem is solved in the paper StackGAN: Text to Photo-realistic Image Synthesis with Stacked Generative Adversarial Networks. The paper includes the problem of generating the captions for the images and then these captions along with the images are used to generate the fake images using StackGAN')

############################################################################################################################################

#Loading Dataset

class BirdDataset(data.Dataset):
    def __init__(self, dataDir, split='train', imgSize=64, transform=None):
        super(BirdDataset,self).__init__()
        self.transform = transform
        self.norm = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
        self.imgSize = imgSize
        self.dataDir = dataDir
        self.filenames, self.caps = self.load_info(dataDir, split)
        self.bbox = self.load_bbox()
        self.classes = self.load_class(dataDir, split)
              
    def load_info(self, dataDir, split):
        filenames = self.load_filenames(dataDir, split)
        captionFile = os.path.join(dataDir, 'birds', split, 'char-CNN-RNN-embeddings.pickle')
        with open (captionFile, 'rb') as f:
            captions = pickle.load(f,encoding='latin1')
            captions = np.array(captions)
            
        
        return filenames, captions
        
    def load_filenames(self, dataDir, split):
        path = os.path.join(dataDir, 'birds', split, 'filenames.pickle')
        with open(path, 'rb') as f:
            filenames = pickle.load(f,encoding='latin1')
       
        return filenames
    
    def load_bbox(self):
        path = os.path.join(self.dataDir,'birds','CUB_200_2011', 'bounding_boxes.txt')
        bbox_data = pd.read_csv(path, delim_whitespace=True, header=None).astype(int)

        filepath = os.path.join(self.dataDir,'birds', 'CUB_200_2011','images.txt')
        df_filenames = pd.read_csv(filepath, delim_whitespace=True, header=None)
        filenames = sorted( list(df_filenames[1]))
        fname_bbox_dict = {x[:-4]:[] for x in filenames} # use filename without '.jpg' extension as a key
        for i in range(len(filenames)):
            data = list(bbox_data.iloc[1][1:])
            k = filenames[i][:-4]
            fname_bbox_dict[k] = data
        return fname_bbox_dict
    
    def load_class(self, dataDir, split):
        path = os.path.join(dataDir, 'birds', split, 'class_info.pickle')
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                classId = pickle.load(f,encoding='latin1')
        else:
            classId = np.arange(len(self.filenames))
        return classId

    def get_img(self, img_path, bbox=None):
        img = Image.open(img_path).convert('RGB')
        width, height = img.size
        if bbox is not None:
            R = int(np.maximum(bbox[2], bbox[3]) * 0.75)
            center_x = int((2 * bbox[0] + bbox[2]) / 2)
            center_y = int((2 * bbox[1] + bbox[3]) / 2)
            y1 = np.maximum(0, center_y - R)
            y2 = np.minimum(height, center_y + R)
            x1 = np.maximum(0, center_x - R)
            x2 = np.minimum(width, center_x + R)
            img = img.crop([x1, y1, x2, y2])
        load_size = int(self.imgSize * 76 / 64)
        img = img.resize((load_size, load_size), Image.BILINEAR)
        if self.transform is not None:
            img = self.transform(img)
        return img

    
    def __getitem__(self, idx):
        key = self.filenames[idx]
        key = key[:-1]
       
        if self.bbox is not None:
            bbox = self.bbox[key]
        else:
            bbox = None
        emb = self.caps[idx, :, :]
        imagePath = os.path.join(self.dataDir,'birds', 'CUB_200_2011', 'images',key +'.jpg')
        image = self.get_img(imagePath, bbox)
        
        # random select a sentence
        sample = np.random.randint(0, emb.shape[0]-1)
        cap = emb[sample, :]
        return image, cap
    
    def __len__(self):
        return len(self.filenames)
    
############################################################################################################################################

st.subheader('Load Data')
@st.cache
def load_data(split):
    
    transform = transforms.Compose([
                transforms.RandomCrop(256),
                transforms.RandomHorizontalFlip(),
                transforms.ToTensor(),
                transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
    
    dataset = BirdDataset(dataDir = 'txt - img/Data/', split=split, transform=transform, imgSize=256)
    loader = DataLoader(dataset, batch_size= 10, shuffle=True, drop_last=True)

    return loader

data_load_state = st.text('Loading data...')

data = load_data('test')

data_load_state.text("Loading Data...Done! (using st.cache)")

############################################################################################################################################
def main():
    st.subheader("Real Images of Sparrow")
    random.seed(42)
    in_dir_data = 'txt - img/Data/birds/CUB_200_2011'
    in_dir_img = os.path.join(in_dir_data, 'images')

    # obtain classes of sparrow species
    img_sparrows = dict()
    cls_sparrows_total = [k for k in os.listdir(in_dir_img) if 'sparrow' in k.lower()]

    # get images of some sparrow classes 
    cls_sparrows = cls_sparrows_total[1::2][:5]
    for dirname in cls_sparrows:
        imgs = list()
        for dp, _, fn in os.walk(os.path.join(in_dir_img, dirname)):
            imgs.extend(fn)
        img_sparrows[dirname] = imgs

    # visualize randomly-chosen images
    n_cls = len(cls_sparrows)
    f, ax = plt.subplots(1, n_cls, figsize=(14, 8))

    for i in range(n_cls):
        cls_name = cls_sparrows[random.randint(0, n_cls - 1)]
        n_img = len(img_sparrows[cls_name])
        img_name = img_sparrows[cls_name][random.randint(0, n_img - 1)]
        path_img = os.path.join(os.path.join(in_dir_img, cls_name), img_name)
        ax[i].imshow(mpimg.imread(path_img))
        ax[i].set_title(cls_name.split('.')[-1].replace('_', ' '),  fontsize=12)

        plt.tight_layout()
    st.pyplot(f)

if __name__ == "__main__":
    main()
    
############################################################################################################################################
def weights_init(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        nn.init.normal_(m.weight.data, 0.0, 0.02)
    elif classname.find('BatchNorm') != -1:
        nn.init.normal_(m.weight.data, 1.0, 0.02)
        nn.init.constant_(m.bias.data, 0)
        
cond_dim = 128
df_dim = 128
gf_dim = 128
z_dim = 100
emb_dim = 1024

def Conv_k3(in_p, out_p, stride=1):
    return nn.Conv2d(in_p, out_p, kernel_size=3, stride=stride, padding=1, bias=False)

class Upblock(nn.Module):
    def __init__(self, inp, outp):
        super(Upblock, self).__init__()
        self.up = nn.Upsample(scale_factor=2, mode='nearest')
        self.conv = Conv_k3(inp, outp)
        self.batch = nn.BatchNorm2d(outp)
        self.relu = nn.ReLU(True)
        
    def forward(self, x):
        o = self.up(x)
        o = self.relu(self.conv(o))
        o = self.batch(o)
        return o

class D_output(nn.Module):
    def __init__(self, have_cond = True):
        super(D_output, self).__init__()
        self.have_cond = have_cond
        self.classifier = nn.Sequential(
            nn.Conv2d(in_channels=1024, out_channels=1, kernel_size=4, stride=4),
            nn.Sigmoid()
        )
        if have_cond:
            cond_part = nn.Sequential(
                Conv_k3(in_p=1024+128, out_p=1024),
                nn.BatchNorm2d(1024),
                nn.LeakyReLU(0.2, inplace=True),
            )
            self.classifier = torch.nn.Sequential(*(list(cond_part)+list(self.classifier)))
        print(self.classifier)
            
    def forward(self, encoded_image, encoded_cond=None):
        if self.have_cond and encoded_cond is not None:
            cond = encoded_cond.view(-1, 128 , 1, 1)
            cond = cond.repeat(1, 1, 4, 4)
            image_with_cond = torch.cat((encoded_image, cond), 1)
        else:
            image_with_cond = encoded_image
        return self.classifier(image_with_cond).view(-1)

class CondAugment_Model(nn.Module):
    def __init__(self):
        super(CondAugment_Model,self).__init__()
        self.fc = nn.Linear(in_features=emb_dim, out_features=cond_dim*2)
        self.relu = nn.ReLU(True)
        
    def convert(self, embed):
        x = self.relu(self.fc(embed))
        mean, sigma = x[:, : cond_dim], x[:, cond_dim:]
        return mean, sigma
    
    def forward(self, x):
        mean, sigma = self.convert(x)
        diag = torch.exp(sigma*0.5)
        normal_dis = (torch.FloatTensor(diag.size()).normal_())
        condition = (diag*normal_dis)+mean
        return condition, mean, sigma

class ResBlock(nn.Module):
    def __init__(self, plane):
        super(ResBlock, self).__init__()
        self.block = nn.Sequential(
            Conv_k3(plane, plane),
            nn.BatchNorm2d(plane),
            nn.ReLU(True),
            Conv_k3(plane, plane),
            nn.BatchNorm2d(plane)
        )
        self.relu = nn.ReLU(True)
        
    def forward(self, x):
        tmp = x
        o = self.block(x)
        o = o + tmp
        return self.relu(o)


#Stage-I GAN

class G_Stage1(nn.Module):
    def __init__(self):
        super(G_Stage1, self).__init__()
        self.CA = CondAugment_Model()
        self.fc = nn.Sequential(
            nn.Linear(in_features=228, out_features=128*8*4*4, bias=False),
            nn.BatchNorm1d(128*8*4*4),
            nn.ReLU(inplace=True)
        )
        self.img = nn.Sequential(
            Upblock(128*8,64*8),
            Upblock(64*8,32*8),
            Upblock(32*8,16*8),
            Upblock(16*8,8*8),
            Conv_k3(8*8, 3),
            nn.Tanh()
        )
        
    def forward(self, noise, emb):
        cond, mean, sigma = self.CA(emb)
        cond = cond.view(noise.size(0), cond_dim, 1, 1)
        x = torch.cat((noise, cond),1)
        x = x.view(-1, 228)
        o = self.fc(x)
        h_code = o.view(-1, 128*8, 4, 4)
        fake_img = self.img(h_code)
        return fake_img, mean, sigma
    
class D_Stage1(nn.Module):
    def __init__(self):
        super(D_Stage1, self).__init__()
        self.encoder = nn.Sequential(
            #c alucalation output size = [(input_size −Kernal +2Padding )/Stride ]+1
            # input is image 3 x 64 x 64  
            nn.Conv2d(in_channels=3, out_channels=128, kernel_size=4, stride=2, padding=1, bias=False),
            nn.LeakyReLU(0.2, inplace=True),# => 128 x 32 x 32 
            
            nn.Conv2d(in_channels=128, out_channels=256, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.2, inplace=True),# => 256 x 16 x 16
            
            nn.Conv2d(in_channels=256, out_channels=512, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.2, inplace=True),# => 512 x 8 x 8
            
            nn.Conv2d(in_channels=512, out_channels=1024, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(1024),
            nn.LeakyReLU(0.2, inplace=True)# => 1024 x 4 x 4
        )
        self.condition_classifier = D_output()
        self.uncondition_classifier = None
        
    def forward(self, image):
        return self.encoder(image)
    
    
#Stage-II GAN

class G_Stage2(nn.Module):
    def __init__(self, G_Stage1):
        super(G_Stage2, self).__init__()
        self.G1 = G_Stage1
        self.CA = CondAugment_Model()
        for p in self.G1.parameters():
            p.requires_grad = False
        self.encoder = nn.Sequential(
            Conv_k3(3, 128),
            nn.ReLU(True),
            nn.Conv2d(128, 128 * 2, 4, 2, 1, bias=False),
            nn.BatchNorm2d(128 * 2),
            nn.ReLU(True),
            nn.Conv2d(128 * 2, 128 * 4, 4, 2, 1, bias=False),
            nn.BatchNorm2d(128 * 4),
            nn.ReLU(True))
        self.combine = nn.Sequential(
            Conv_k3(640, 512),
            nn.BatchNorm2d(512),
            nn.ReLU(True)
        )
        self.residual = nn.Sequential(
            ResBlock(512),
            ResBlock(512),
            ResBlock(512),
            ResBlock(512)
        )
        self.decoder = nn.Sequential(
            Upblock(512,256),
            Upblock(256,128),
            Upblock(128,64),
            Upblock(64,32),
            Conv_k3(32,3),
            nn.Tanh()
        )
        
    def forward(self, noise, emb):
        init_image, _, _ = self.G1(noise, emb)
        encoded = self.encoder(init_image)
        
        cond, m, s = self.CA(emb)
        cond = cond.view(-1, 128, 1, 1)
        cond = cond.repeat(1, 1, 16, 16)
        
        encoded_cond = torch.cat([encoded, cond],1)
        img_feature = self.combine(encoded_cond)
        img_feature = self.residual(img_feature)
        img = self.decoder(img_feature)
        
        return init_image, img, m, s
    
    
class D_Stage2(nn.Module):
    def __init__(self):
        super(D_Stage2, self).__init__()
        self.img_encoder = nn.Sequential(
            # start 3 x 256 x 256
            nn.Conv2d(3, 128, 4, 2, 1, bias=False), #=> 128 x 128 x 128
            nn.LeakyReLU(0.2, True),
            
            nn.Conv2d(128, 256, 4, 2, 1, bias=False), #=> 256 x 64 x 64
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.2, True),
            
            nn.Conv2d(256, 512, 4, 2, 1, bias=False), #=> 512 x 32 x 32
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.2, True),
            
            nn.Conv2d(512, 1024, 4, 2, 1, bias=False), #=> 1024 x 16 x 16
            nn.BatchNorm2d(1024),
            nn.LeakyReLU(0.2, True),
            
            nn.Conv2d(1024, 2048, 4, 2, 1, bias=False), #=> 2048 x 8 x 8
            nn.BatchNorm2d(2048),
            nn.LeakyReLU(0.2, True),
            
            nn.Conv2d(2048, 4096, 4, 2, 1, bias=False), #=> 4096 x 4 x 4
            nn.BatchNorm2d(4096),
            nn.LeakyReLU(0.2, True),
            
            Conv_k3(4096, 2048), # 2048 x 4 x 4
            nn.BatchNorm2d(2048),
            nn.LeakyReLU(0.2, True),
            Conv_k3(2048, 1024), # 1024 x 4 x 4
            nn.BatchNorm2d(1024),
            nn.LeakyReLU(0.2, True)
        )
        
        self.condition_classifier = D_output()
        self.uncondition_classifier = D_output(have_cond=False)
        
    def forward(self, img):
        img_feature = self.img_encoder(img)
        return img_feature


# In[105]:

############################################################################################################################################

def final_fun(loader):
    
    #load the saved model 
    device = torch.device('cpu')
    G1 = G_Stage1().to(device)
    G1checkpoint = torch.load('results/netG_epoch_600.pth', map_location=torch.device('cpu'))
    G1.load_state_dict(G1checkpoint)
    G1.eval()

    netG = G_Stage2(G1).to(device)
    G2checkpoint = torch.load('results2/results2_netG2_epoch_420.pth', map_location=torch.device('cpu'))
    netG.load_state_dict(G2checkpoint)
    netG.eval()
    
    loader = iter(loader)
    imgTensor, captions = next(loader)

    batch_size = 10
 
    with torch.no_grad():# Generate image grid
        
        noise = torch.rand(batch_size, z_dim, 1, 1).to(device)
        cap = captions.to(device)
        init_imgs, fake_imgs, m, s = netG(noise, cap)
        
        grid = make_grid(fake_imgs.detach().cpu()[:5], padding = 4, nrow=5).permute(1, 2, 0).numpy()
        
        return grid


# In[ ]:

st.subheader("Generating Fake Images of Birds")

if st.button('Generate Five Samples'):
    fig = plt.figure(figsize=(25, 10), dpi=300)
    grid = final_fun(data)
    plt.axis('off')
    plt.title('FAKE IMAGES GENERATED')
    # Plot Image Grid
    plt.imshow(grid)
    st.pyplot(fig)

st.sidebar.markdown('<a href="https://github.com/RetroX6">GitHub</a>', unsafe_allow_html=True)
st.sidebar.markdown('<a href="https://www.linkedin.com/in/gaurav-thakur-055785159/">LinkedIn</a>', unsafe_allow_html=True)
