#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_6404612215142923466) {
   out_6404612215142923466[0] = delta_x[0] + nom_x[0];
   out_6404612215142923466[1] = delta_x[1] + nom_x[1];
   out_6404612215142923466[2] = delta_x[2] + nom_x[2];
   out_6404612215142923466[3] = delta_x[3] + nom_x[3];
   out_6404612215142923466[4] = delta_x[4] + nom_x[4];
   out_6404612215142923466[5] = delta_x[5] + nom_x[5];
   out_6404612215142923466[6] = delta_x[6] + nom_x[6];
   out_6404612215142923466[7] = delta_x[7] + nom_x[7];
   out_6404612215142923466[8] = delta_x[8] + nom_x[8];
   out_6404612215142923466[9] = delta_x[9] + nom_x[9];
   out_6404612215142923466[10] = delta_x[10] + nom_x[10];
   out_6404612215142923466[11] = delta_x[11] + nom_x[11];
   out_6404612215142923466[12] = delta_x[12] + nom_x[12];
   out_6404612215142923466[13] = delta_x[13] + nom_x[13];
   out_6404612215142923466[14] = delta_x[14] + nom_x[14];
   out_6404612215142923466[15] = delta_x[15] + nom_x[15];
   out_6404612215142923466[16] = delta_x[16] + nom_x[16];
   out_6404612215142923466[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8928511729536831732) {
   out_8928511729536831732[0] = -nom_x[0] + true_x[0];
   out_8928511729536831732[1] = -nom_x[1] + true_x[1];
   out_8928511729536831732[2] = -nom_x[2] + true_x[2];
   out_8928511729536831732[3] = -nom_x[3] + true_x[3];
   out_8928511729536831732[4] = -nom_x[4] + true_x[4];
   out_8928511729536831732[5] = -nom_x[5] + true_x[5];
   out_8928511729536831732[6] = -nom_x[6] + true_x[6];
   out_8928511729536831732[7] = -nom_x[7] + true_x[7];
   out_8928511729536831732[8] = -nom_x[8] + true_x[8];
   out_8928511729536831732[9] = -nom_x[9] + true_x[9];
   out_8928511729536831732[10] = -nom_x[10] + true_x[10];
   out_8928511729536831732[11] = -nom_x[11] + true_x[11];
   out_8928511729536831732[12] = -nom_x[12] + true_x[12];
   out_8928511729536831732[13] = -nom_x[13] + true_x[13];
   out_8928511729536831732[14] = -nom_x[14] + true_x[14];
   out_8928511729536831732[15] = -nom_x[15] + true_x[15];
   out_8928511729536831732[16] = -nom_x[16] + true_x[16];
   out_8928511729536831732[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_6801514816147998315) {
   out_6801514816147998315[0] = 1.0;
   out_6801514816147998315[1] = 0.0;
   out_6801514816147998315[2] = 0.0;
   out_6801514816147998315[3] = 0.0;
   out_6801514816147998315[4] = 0.0;
   out_6801514816147998315[5] = 0.0;
   out_6801514816147998315[6] = 0.0;
   out_6801514816147998315[7] = 0.0;
   out_6801514816147998315[8] = 0.0;
   out_6801514816147998315[9] = 0.0;
   out_6801514816147998315[10] = 0.0;
   out_6801514816147998315[11] = 0.0;
   out_6801514816147998315[12] = 0.0;
   out_6801514816147998315[13] = 0.0;
   out_6801514816147998315[14] = 0.0;
   out_6801514816147998315[15] = 0.0;
   out_6801514816147998315[16] = 0.0;
   out_6801514816147998315[17] = 0.0;
   out_6801514816147998315[18] = 0.0;
   out_6801514816147998315[19] = 1.0;
   out_6801514816147998315[20] = 0.0;
   out_6801514816147998315[21] = 0.0;
   out_6801514816147998315[22] = 0.0;
   out_6801514816147998315[23] = 0.0;
   out_6801514816147998315[24] = 0.0;
   out_6801514816147998315[25] = 0.0;
   out_6801514816147998315[26] = 0.0;
   out_6801514816147998315[27] = 0.0;
   out_6801514816147998315[28] = 0.0;
   out_6801514816147998315[29] = 0.0;
   out_6801514816147998315[30] = 0.0;
   out_6801514816147998315[31] = 0.0;
   out_6801514816147998315[32] = 0.0;
   out_6801514816147998315[33] = 0.0;
   out_6801514816147998315[34] = 0.0;
   out_6801514816147998315[35] = 0.0;
   out_6801514816147998315[36] = 0.0;
   out_6801514816147998315[37] = 0.0;
   out_6801514816147998315[38] = 1.0;
   out_6801514816147998315[39] = 0.0;
   out_6801514816147998315[40] = 0.0;
   out_6801514816147998315[41] = 0.0;
   out_6801514816147998315[42] = 0.0;
   out_6801514816147998315[43] = 0.0;
   out_6801514816147998315[44] = 0.0;
   out_6801514816147998315[45] = 0.0;
   out_6801514816147998315[46] = 0.0;
   out_6801514816147998315[47] = 0.0;
   out_6801514816147998315[48] = 0.0;
   out_6801514816147998315[49] = 0.0;
   out_6801514816147998315[50] = 0.0;
   out_6801514816147998315[51] = 0.0;
   out_6801514816147998315[52] = 0.0;
   out_6801514816147998315[53] = 0.0;
   out_6801514816147998315[54] = 0.0;
   out_6801514816147998315[55] = 0.0;
   out_6801514816147998315[56] = 0.0;
   out_6801514816147998315[57] = 1.0;
   out_6801514816147998315[58] = 0.0;
   out_6801514816147998315[59] = 0.0;
   out_6801514816147998315[60] = 0.0;
   out_6801514816147998315[61] = 0.0;
   out_6801514816147998315[62] = 0.0;
   out_6801514816147998315[63] = 0.0;
   out_6801514816147998315[64] = 0.0;
   out_6801514816147998315[65] = 0.0;
   out_6801514816147998315[66] = 0.0;
   out_6801514816147998315[67] = 0.0;
   out_6801514816147998315[68] = 0.0;
   out_6801514816147998315[69] = 0.0;
   out_6801514816147998315[70] = 0.0;
   out_6801514816147998315[71] = 0.0;
   out_6801514816147998315[72] = 0.0;
   out_6801514816147998315[73] = 0.0;
   out_6801514816147998315[74] = 0.0;
   out_6801514816147998315[75] = 0.0;
   out_6801514816147998315[76] = 1.0;
   out_6801514816147998315[77] = 0.0;
   out_6801514816147998315[78] = 0.0;
   out_6801514816147998315[79] = 0.0;
   out_6801514816147998315[80] = 0.0;
   out_6801514816147998315[81] = 0.0;
   out_6801514816147998315[82] = 0.0;
   out_6801514816147998315[83] = 0.0;
   out_6801514816147998315[84] = 0.0;
   out_6801514816147998315[85] = 0.0;
   out_6801514816147998315[86] = 0.0;
   out_6801514816147998315[87] = 0.0;
   out_6801514816147998315[88] = 0.0;
   out_6801514816147998315[89] = 0.0;
   out_6801514816147998315[90] = 0.0;
   out_6801514816147998315[91] = 0.0;
   out_6801514816147998315[92] = 0.0;
   out_6801514816147998315[93] = 0.0;
   out_6801514816147998315[94] = 0.0;
   out_6801514816147998315[95] = 1.0;
   out_6801514816147998315[96] = 0.0;
   out_6801514816147998315[97] = 0.0;
   out_6801514816147998315[98] = 0.0;
   out_6801514816147998315[99] = 0.0;
   out_6801514816147998315[100] = 0.0;
   out_6801514816147998315[101] = 0.0;
   out_6801514816147998315[102] = 0.0;
   out_6801514816147998315[103] = 0.0;
   out_6801514816147998315[104] = 0.0;
   out_6801514816147998315[105] = 0.0;
   out_6801514816147998315[106] = 0.0;
   out_6801514816147998315[107] = 0.0;
   out_6801514816147998315[108] = 0.0;
   out_6801514816147998315[109] = 0.0;
   out_6801514816147998315[110] = 0.0;
   out_6801514816147998315[111] = 0.0;
   out_6801514816147998315[112] = 0.0;
   out_6801514816147998315[113] = 0.0;
   out_6801514816147998315[114] = 1.0;
   out_6801514816147998315[115] = 0.0;
   out_6801514816147998315[116] = 0.0;
   out_6801514816147998315[117] = 0.0;
   out_6801514816147998315[118] = 0.0;
   out_6801514816147998315[119] = 0.0;
   out_6801514816147998315[120] = 0.0;
   out_6801514816147998315[121] = 0.0;
   out_6801514816147998315[122] = 0.0;
   out_6801514816147998315[123] = 0.0;
   out_6801514816147998315[124] = 0.0;
   out_6801514816147998315[125] = 0.0;
   out_6801514816147998315[126] = 0.0;
   out_6801514816147998315[127] = 0.0;
   out_6801514816147998315[128] = 0.0;
   out_6801514816147998315[129] = 0.0;
   out_6801514816147998315[130] = 0.0;
   out_6801514816147998315[131] = 0.0;
   out_6801514816147998315[132] = 0.0;
   out_6801514816147998315[133] = 1.0;
   out_6801514816147998315[134] = 0.0;
   out_6801514816147998315[135] = 0.0;
   out_6801514816147998315[136] = 0.0;
   out_6801514816147998315[137] = 0.0;
   out_6801514816147998315[138] = 0.0;
   out_6801514816147998315[139] = 0.0;
   out_6801514816147998315[140] = 0.0;
   out_6801514816147998315[141] = 0.0;
   out_6801514816147998315[142] = 0.0;
   out_6801514816147998315[143] = 0.0;
   out_6801514816147998315[144] = 0.0;
   out_6801514816147998315[145] = 0.0;
   out_6801514816147998315[146] = 0.0;
   out_6801514816147998315[147] = 0.0;
   out_6801514816147998315[148] = 0.0;
   out_6801514816147998315[149] = 0.0;
   out_6801514816147998315[150] = 0.0;
   out_6801514816147998315[151] = 0.0;
   out_6801514816147998315[152] = 1.0;
   out_6801514816147998315[153] = 0.0;
   out_6801514816147998315[154] = 0.0;
   out_6801514816147998315[155] = 0.0;
   out_6801514816147998315[156] = 0.0;
   out_6801514816147998315[157] = 0.0;
   out_6801514816147998315[158] = 0.0;
   out_6801514816147998315[159] = 0.0;
   out_6801514816147998315[160] = 0.0;
   out_6801514816147998315[161] = 0.0;
   out_6801514816147998315[162] = 0.0;
   out_6801514816147998315[163] = 0.0;
   out_6801514816147998315[164] = 0.0;
   out_6801514816147998315[165] = 0.0;
   out_6801514816147998315[166] = 0.0;
   out_6801514816147998315[167] = 0.0;
   out_6801514816147998315[168] = 0.0;
   out_6801514816147998315[169] = 0.0;
   out_6801514816147998315[170] = 0.0;
   out_6801514816147998315[171] = 1.0;
   out_6801514816147998315[172] = 0.0;
   out_6801514816147998315[173] = 0.0;
   out_6801514816147998315[174] = 0.0;
   out_6801514816147998315[175] = 0.0;
   out_6801514816147998315[176] = 0.0;
   out_6801514816147998315[177] = 0.0;
   out_6801514816147998315[178] = 0.0;
   out_6801514816147998315[179] = 0.0;
   out_6801514816147998315[180] = 0.0;
   out_6801514816147998315[181] = 0.0;
   out_6801514816147998315[182] = 0.0;
   out_6801514816147998315[183] = 0.0;
   out_6801514816147998315[184] = 0.0;
   out_6801514816147998315[185] = 0.0;
   out_6801514816147998315[186] = 0.0;
   out_6801514816147998315[187] = 0.0;
   out_6801514816147998315[188] = 0.0;
   out_6801514816147998315[189] = 0.0;
   out_6801514816147998315[190] = 1.0;
   out_6801514816147998315[191] = 0.0;
   out_6801514816147998315[192] = 0.0;
   out_6801514816147998315[193] = 0.0;
   out_6801514816147998315[194] = 0.0;
   out_6801514816147998315[195] = 0.0;
   out_6801514816147998315[196] = 0.0;
   out_6801514816147998315[197] = 0.0;
   out_6801514816147998315[198] = 0.0;
   out_6801514816147998315[199] = 0.0;
   out_6801514816147998315[200] = 0.0;
   out_6801514816147998315[201] = 0.0;
   out_6801514816147998315[202] = 0.0;
   out_6801514816147998315[203] = 0.0;
   out_6801514816147998315[204] = 0.0;
   out_6801514816147998315[205] = 0.0;
   out_6801514816147998315[206] = 0.0;
   out_6801514816147998315[207] = 0.0;
   out_6801514816147998315[208] = 0.0;
   out_6801514816147998315[209] = 1.0;
   out_6801514816147998315[210] = 0.0;
   out_6801514816147998315[211] = 0.0;
   out_6801514816147998315[212] = 0.0;
   out_6801514816147998315[213] = 0.0;
   out_6801514816147998315[214] = 0.0;
   out_6801514816147998315[215] = 0.0;
   out_6801514816147998315[216] = 0.0;
   out_6801514816147998315[217] = 0.0;
   out_6801514816147998315[218] = 0.0;
   out_6801514816147998315[219] = 0.0;
   out_6801514816147998315[220] = 0.0;
   out_6801514816147998315[221] = 0.0;
   out_6801514816147998315[222] = 0.0;
   out_6801514816147998315[223] = 0.0;
   out_6801514816147998315[224] = 0.0;
   out_6801514816147998315[225] = 0.0;
   out_6801514816147998315[226] = 0.0;
   out_6801514816147998315[227] = 0.0;
   out_6801514816147998315[228] = 1.0;
   out_6801514816147998315[229] = 0.0;
   out_6801514816147998315[230] = 0.0;
   out_6801514816147998315[231] = 0.0;
   out_6801514816147998315[232] = 0.0;
   out_6801514816147998315[233] = 0.0;
   out_6801514816147998315[234] = 0.0;
   out_6801514816147998315[235] = 0.0;
   out_6801514816147998315[236] = 0.0;
   out_6801514816147998315[237] = 0.0;
   out_6801514816147998315[238] = 0.0;
   out_6801514816147998315[239] = 0.0;
   out_6801514816147998315[240] = 0.0;
   out_6801514816147998315[241] = 0.0;
   out_6801514816147998315[242] = 0.0;
   out_6801514816147998315[243] = 0.0;
   out_6801514816147998315[244] = 0.0;
   out_6801514816147998315[245] = 0.0;
   out_6801514816147998315[246] = 0.0;
   out_6801514816147998315[247] = 1.0;
   out_6801514816147998315[248] = 0.0;
   out_6801514816147998315[249] = 0.0;
   out_6801514816147998315[250] = 0.0;
   out_6801514816147998315[251] = 0.0;
   out_6801514816147998315[252] = 0.0;
   out_6801514816147998315[253] = 0.0;
   out_6801514816147998315[254] = 0.0;
   out_6801514816147998315[255] = 0.0;
   out_6801514816147998315[256] = 0.0;
   out_6801514816147998315[257] = 0.0;
   out_6801514816147998315[258] = 0.0;
   out_6801514816147998315[259] = 0.0;
   out_6801514816147998315[260] = 0.0;
   out_6801514816147998315[261] = 0.0;
   out_6801514816147998315[262] = 0.0;
   out_6801514816147998315[263] = 0.0;
   out_6801514816147998315[264] = 0.0;
   out_6801514816147998315[265] = 0.0;
   out_6801514816147998315[266] = 1.0;
   out_6801514816147998315[267] = 0.0;
   out_6801514816147998315[268] = 0.0;
   out_6801514816147998315[269] = 0.0;
   out_6801514816147998315[270] = 0.0;
   out_6801514816147998315[271] = 0.0;
   out_6801514816147998315[272] = 0.0;
   out_6801514816147998315[273] = 0.0;
   out_6801514816147998315[274] = 0.0;
   out_6801514816147998315[275] = 0.0;
   out_6801514816147998315[276] = 0.0;
   out_6801514816147998315[277] = 0.0;
   out_6801514816147998315[278] = 0.0;
   out_6801514816147998315[279] = 0.0;
   out_6801514816147998315[280] = 0.0;
   out_6801514816147998315[281] = 0.0;
   out_6801514816147998315[282] = 0.0;
   out_6801514816147998315[283] = 0.0;
   out_6801514816147998315[284] = 0.0;
   out_6801514816147998315[285] = 1.0;
   out_6801514816147998315[286] = 0.0;
   out_6801514816147998315[287] = 0.0;
   out_6801514816147998315[288] = 0.0;
   out_6801514816147998315[289] = 0.0;
   out_6801514816147998315[290] = 0.0;
   out_6801514816147998315[291] = 0.0;
   out_6801514816147998315[292] = 0.0;
   out_6801514816147998315[293] = 0.0;
   out_6801514816147998315[294] = 0.0;
   out_6801514816147998315[295] = 0.0;
   out_6801514816147998315[296] = 0.0;
   out_6801514816147998315[297] = 0.0;
   out_6801514816147998315[298] = 0.0;
   out_6801514816147998315[299] = 0.0;
   out_6801514816147998315[300] = 0.0;
   out_6801514816147998315[301] = 0.0;
   out_6801514816147998315[302] = 0.0;
   out_6801514816147998315[303] = 0.0;
   out_6801514816147998315[304] = 1.0;
   out_6801514816147998315[305] = 0.0;
   out_6801514816147998315[306] = 0.0;
   out_6801514816147998315[307] = 0.0;
   out_6801514816147998315[308] = 0.0;
   out_6801514816147998315[309] = 0.0;
   out_6801514816147998315[310] = 0.0;
   out_6801514816147998315[311] = 0.0;
   out_6801514816147998315[312] = 0.0;
   out_6801514816147998315[313] = 0.0;
   out_6801514816147998315[314] = 0.0;
   out_6801514816147998315[315] = 0.0;
   out_6801514816147998315[316] = 0.0;
   out_6801514816147998315[317] = 0.0;
   out_6801514816147998315[318] = 0.0;
   out_6801514816147998315[319] = 0.0;
   out_6801514816147998315[320] = 0.0;
   out_6801514816147998315[321] = 0.0;
   out_6801514816147998315[322] = 0.0;
   out_6801514816147998315[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_9011020625270980343) {
   out_9011020625270980343[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_9011020625270980343[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_9011020625270980343[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_9011020625270980343[3] = dt*state[12] + state[3];
   out_9011020625270980343[4] = dt*state[13] + state[4];
   out_9011020625270980343[5] = dt*state[14] + state[5];
   out_9011020625270980343[6] = state[6];
   out_9011020625270980343[7] = state[7];
   out_9011020625270980343[8] = state[8];
   out_9011020625270980343[9] = state[9];
   out_9011020625270980343[10] = state[10];
   out_9011020625270980343[11] = state[11];
   out_9011020625270980343[12] = state[12];
   out_9011020625270980343[13] = state[13];
   out_9011020625270980343[14] = state[14];
   out_9011020625270980343[15] = state[15];
   out_9011020625270980343[16] = state[16];
   out_9011020625270980343[17] = state[17];
}
void F_fun(double *state, double dt, double *out_5745440695796585215) {
   out_5745440695796585215[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5745440695796585215[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5745440695796585215[2] = 0;
   out_5745440695796585215[3] = 0;
   out_5745440695796585215[4] = 0;
   out_5745440695796585215[5] = 0;
   out_5745440695796585215[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5745440695796585215[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5745440695796585215[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5745440695796585215[9] = 0;
   out_5745440695796585215[10] = 0;
   out_5745440695796585215[11] = 0;
   out_5745440695796585215[12] = 0;
   out_5745440695796585215[13] = 0;
   out_5745440695796585215[14] = 0;
   out_5745440695796585215[15] = 0;
   out_5745440695796585215[16] = 0;
   out_5745440695796585215[17] = 0;
   out_5745440695796585215[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5745440695796585215[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5745440695796585215[20] = 0;
   out_5745440695796585215[21] = 0;
   out_5745440695796585215[22] = 0;
   out_5745440695796585215[23] = 0;
   out_5745440695796585215[24] = 0;
   out_5745440695796585215[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5745440695796585215[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5745440695796585215[27] = 0;
   out_5745440695796585215[28] = 0;
   out_5745440695796585215[29] = 0;
   out_5745440695796585215[30] = 0;
   out_5745440695796585215[31] = 0;
   out_5745440695796585215[32] = 0;
   out_5745440695796585215[33] = 0;
   out_5745440695796585215[34] = 0;
   out_5745440695796585215[35] = 0;
   out_5745440695796585215[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5745440695796585215[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5745440695796585215[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5745440695796585215[39] = 0;
   out_5745440695796585215[40] = 0;
   out_5745440695796585215[41] = 0;
   out_5745440695796585215[42] = 0;
   out_5745440695796585215[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5745440695796585215[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5745440695796585215[45] = 0;
   out_5745440695796585215[46] = 0;
   out_5745440695796585215[47] = 0;
   out_5745440695796585215[48] = 0;
   out_5745440695796585215[49] = 0;
   out_5745440695796585215[50] = 0;
   out_5745440695796585215[51] = 0;
   out_5745440695796585215[52] = 0;
   out_5745440695796585215[53] = 0;
   out_5745440695796585215[54] = 0;
   out_5745440695796585215[55] = 0;
   out_5745440695796585215[56] = 0;
   out_5745440695796585215[57] = 1;
   out_5745440695796585215[58] = 0;
   out_5745440695796585215[59] = 0;
   out_5745440695796585215[60] = 0;
   out_5745440695796585215[61] = 0;
   out_5745440695796585215[62] = 0;
   out_5745440695796585215[63] = 0;
   out_5745440695796585215[64] = 0;
   out_5745440695796585215[65] = 0;
   out_5745440695796585215[66] = dt;
   out_5745440695796585215[67] = 0;
   out_5745440695796585215[68] = 0;
   out_5745440695796585215[69] = 0;
   out_5745440695796585215[70] = 0;
   out_5745440695796585215[71] = 0;
   out_5745440695796585215[72] = 0;
   out_5745440695796585215[73] = 0;
   out_5745440695796585215[74] = 0;
   out_5745440695796585215[75] = 0;
   out_5745440695796585215[76] = 1;
   out_5745440695796585215[77] = 0;
   out_5745440695796585215[78] = 0;
   out_5745440695796585215[79] = 0;
   out_5745440695796585215[80] = 0;
   out_5745440695796585215[81] = 0;
   out_5745440695796585215[82] = 0;
   out_5745440695796585215[83] = 0;
   out_5745440695796585215[84] = 0;
   out_5745440695796585215[85] = dt;
   out_5745440695796585215[86] = 0;
   out_5745440695796585215[87] = 0;
   out_5745440695796585215[88] = 0;
   out_5745440695796585215[89] = 0;
   out_5745440695796585215[90] = 0;
   out_5745440695796585215[91] = 0;
   out_5745440695796585215[92] = 0;
   out_5745440695796585215[93] = 0;
   out_5745440695796585215[94] = 0;
   out_5745440695796585215[95] = 1;
   out_5745440695796585215[96] = 0;
   out_5745440695796585215[97] = 0;
   out_5745440695796585215[98] = 0;
   out_5745440695796585215[99] = 0;
   out_5745440695796585215[100] = 0;
   out_5745440695796585215[101] = 0;
   out_5745440695796585215[102] = 0;
   out_5745440695796585215[103] = 0;
   out_5745440695796585215[104] = dt;
   out_5745440695796585215[105] = 0;
   out_5745440695796585215[106] = 0;
   out_5745440695796585215[107] = 0;
   out_5745440695796585215[108] = 0;
   out_5745440695796585215[109] = 0;
   out_5745440695796585215[110] = 0;
   out_5745440695796585215[111] = 0;
   out_5745440695796585215[112] = 0;
   out_5745440695796585215[113] = 0;
   out_5745440695796585215[114] = 1;
   out_5745440695796585215[115] = 0;
   out_5745440695796585215[116] = 0;
   out_5745440695796585215[117] = 0;
   out_5745440695796585215[118] = 0;
   out_5745440695796585215[119] = 0;
   out_5745440695796585215[120] = 0;
   out_5745440695796585215[121] = 0;
   out_5745440695796585215[122] = 0;
   out_5745440695796585215[123] = 0;
   out_5745440695796585215[124] = 0;
   out_5745440695796585215[125] = 0;
   out_5745440695796585215[126] = 0;
   out_5745440695796585215[127] = 0;
   out_5745440695796585215[128] = 0;
   out_5745440695796585215[129] = 0;
   out_5745440695796585215[130] = 0;
   out_5745440695796585215[131] = 0;
   out_5745440695796585215[132] = 0;
   out_5745440695796585215[133] = 1;
   out_5745440695796585215[134] = 0;
   out_5745440695796585215[135] = 0;
   out_5745440695796585215[136] = 0;
   out_5745440695796585215[137] = 0;
   out_5745440695796585215[138] = 0;
   out_5745440695796585215[139] = 0;
   out_5745440695796585215[140] = 0;
   out_5745440695796585215[141] = 0;
   out_5745440695796585215[142] = 0;
   out_5745440695796585215[143] = 0;
   out_5745440695796585215[144] = 0;
   out_5745440695796585215[145] = 0;
   out_5745440695796585215[146] = 0;
   out_5745440695796585215[147] = 0;
   out_5745440695796585215[148] = 0;
   out_5745440695796585215[149] = 0;
   out_5745440695796585215[150] = 0;
   out_5745440695796585215[151] = 0;
   out_5745440695796585215[152] = 1;
   out_5745440695796585215[153] = 0;
   out_5745440695796585215[154] = 0;
   out_5745440695796585215[155] = 0;
   out_5745440695796585215[156] = 0;
   out_5745440695796585215[157] = 0;
   out_5745440695796585215[158] = 0;
   out_5745440695796585215[159] = 0;
   out_5745440695796585215[160] = 0;
   out_5745440695796585215[161] = 0;
   out_5745440695796585215[162] = 0;
   out_5745440695796585215[163] = 0;
   out_5745440695796585215[164] = 0;
   out_5745440695796585215[165] = 0;
   out_5745440695796585215[166] = 0;
   out_5745440695796585215[167] = 0;
   out_5745440695796585215[168] = 0;
   out_5745440695796585215[169] = 0;
   out_5745440695796585215[170] = 0;
   out_5745440695796585215[171] = 1;
   out_5745440695796585215[172] = 0;
   out_5745440695796585215[173] = 0;
   out_5745440695796585215[174] = 0;
   out_5745440695796585215[175] = 0;
   out_5745440695796585215[176] = 0;
   out_5745440695796585215[177] = 0;
   out_5745440695796585215[178] = 0;
   out_5745440695796585215[179] = 0;
   out_5745440695796585215[180] = 0;
   out_5745440695796585215[181] = 0;
   out_5745440695796585215[182] = 0;
   out_5745440695796585215[183] = 0;
   out_5745440695796585215[184] = 0;
   out_5745440695796585215[185] = 0;
   out_5745440695796585215[186] = 0;
   out_5745440695796585215[187] = 0;
   out_5745440695796585215[188] = 0;
   out_5745440695796585215[189] = 0;
   out_5745440695796585215[190] = 1;
   out_5745440695796585215[191] = 0;
   out_5745440695796585215[192] = 0;
   out_5745440695796585215[193] = 0;
   out_5745440695796585215[194] = 0;
   out_5745440695796585215[195] = 0;
   out_5745440695796585215[196] = 0;
   out_5745440695796585215[197] = 0;
   out_5745440695796585215[198] = 0;
   out_5745440695796585215[199] = 0;
   out_5745440695796585215[200] = 0;
   out_5745440695796585215[201] = 0;
   out_5745440695796585215[202] = 0;
   out_5745440695796585215[203] = 0;
   out_5745440695796585215[204] = 0;
   out_5745440695796585215[205] = 0;
   out_5745440695796585215[206] = 0;
   out_5745440695796585215[207] = 0;
   out_5745440695796585215[208] = 0;
   out_5745440695796585215[209] = 1;
   out_5745440695796585215[210] = 0;
   out_5745440695796585215[211] = 0;
   out_5745440695796585215[212] = 0;
   out_5745440695796585215[213] = 0;
   out_5745440695796585215[214] = 0;
   out_5745440695796585215[215] = 0;
   out_5745440695796585215[216] = 0;
   out_5745440695796585215[217] = 0;
   out_5745440695796585215[218] = 0;
   out_5745440695796585215[219] = 0;
   out_5745440695796585215[220] = 0;
   out_5745440695796585215[221] = 0;
   out_5745440695796585215[222] = 0;
   out_5745440695796585215[223] = 0;
   out_5745440695796585215[224] = 0;
   out_5745440695796585215[225] = 0;
   out_5745440695796585215[226] = 0;
   out_5745440695796585215[227] = 0;
   out_5745440695796585215[228] = 1;
   out_5745440695796585215[229] = 0;
   out_5745440695796585215[230] = 0;
   out_5745440695796585215[231] = 0;
   out_5745440695796585215[232] = 0;
   out_5745440695796585215[233] = 0;
   out_5745440695796585215[234] = 0;
   out_5745440695796585215[235] = 0;
   out_5745440695796585215[236] = 0;
   out_5745440695796585215[237] = 0;
   out_5745440695796585215[238] = 0;
   out_5745440695796585215[239] = 0;
   out_5745440695796585215[240] = 0;
   out_5745440695796585215[241] = 0;
   out_5745440695796585215[242] = 0;
   out_5745440695796585215[243] = 0;
   out_5745440695796585215[244] = 0;
   out_5745440695796585215[245] = 0;
   out_5745440695796585215[246] = 0;
   out_5745440695796585215[247] = 1;
   out_5745440695796585215[248] = 0;
   out_5745440695796585215[249] = 0;
   out_5745440695796585215[250] = 0;
   out_5745440695796585215[251] = 0;
   out_5745440695796585215[252] = 0;
   out_5745440695796585215[253] = 0;
   out_5745440695796585215[254] = 0;
   out_5745440695796585215[255] = 0;
   out_5745440695796585215[256] = 0;
   out_5745440695796585215[257] = 0;
   out_5745440695796585215[258] = 0;
   out_5745440695796585215[259] = 0;
   out_5745440695796585215[260] = 0;
   out_5745440695796585215[261] = 0;
   out_5745440695796585215[262] = 0;
   out_5745440695796585215[263] = 0;
   out_5745440695796585215[264] = 0;
   out_5745440695796585215[265] = 0;
   out_5745440695796585215[266] = 1;
   out_5745440695796585215[267] = 0;
   out_5745440695796585215[268] = 0;
   out_5745440695796585215[269] = 0;
   out_5745440695796585215[270] = 0;
   out_5745440695796585215[271] = 0;
   out_5745440695796585215[272] = 0;
   out_5745440695796585215[273] = 0;
   out_5745440695796585215[274] = 0;
   out_5745440695796585215[275] = 0;
   out_5745440695796585215[276] = 0;
   out_5745440695796585215[277] = 0;
   out_5745440695796585215[278] = 0;
   out_5745440695796585215[279] = 0;
   out_5745440695796585215[280] = 0;
   out_5745440695796585215[281] = 0;
   out_5745440695796585215[282] = 0;
   out_5745440695796585215[283] = 0;
   out_5745440695796585215[284] = 0;
   out_5745440695796585215[285] = 1;
   out_5745440695796585215[286] = 0;
   out_5745440695796585215[287] = 0;
   out_5745440695796585215[288] = 0;
   out_5745440695796585215[289] = 0;
   out_5745440695796585215[290] = 0;
   out_5745440695796585215[291] = 0;
   out_5745440695796585215[292] = 0;
   out_5745440695796585215[293] = 0;
   out_5745440695796585215[294] = 0;
   out_5745440695796585215[295] = 0;
   out_5745440695796585215[296] = 0;
   out_5745440695796585215[297] = 0;
   out_5745440695796585215[298] = 0;
   out_5745440695796585215[299] = 0;
   out_5745440695796585215[300] = 0;
   out_5745440695796585215[301] = 0;
   out_5745440695796585215[302] = 0;
   out_5745440695796585215[303] = 0;
   out_5745440695796585215[304] = 1;
   out_5745440695796585215[305] = 0;
   out_5745440695796585215[306] = 0;
   out_5745440695796585215[307] = 0;
   out_5745440695796585215[308] = 0;
   out_5745440695796585215[309] = 0;
   out_5745440695796585215[310] = 0;
   out_5745440695796585215[311] = 0;
   out_5745440695796585215[312] = 0;
   out_5745440695796585215[313] = 0;
   out_5745440695796585215[314] = 0;
   out_5745440695796585215[315] = 0;
   out_5745440695796585215[316] = 0;
   out_5745440695796585215[317] = 0;
   out_5745440695796585215[318] = 0;
   out_5745440695796585215[319] = 0;
   out_5745440695796585215[320] = 0;
   out_5745440695796585215[321] = 0;
   out_5745440695796585215[322] = 0;
   out_5745440695796585215[323] = 1;
}
void h_4(double *state, double *unused, double *out_3972431218962943054) {
   out_3972431218962943054[0] = state[6] + state[9];
   out_3972431218962943054[1] = state[7] + state[10];
   out_3972431218962943054[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_7873422047717645729) {
   out_7873422047717645729[0] = 0;
   out_7873422047717645729[1] = 0;
   out_7873422047717645729[2] = 0;
   out_7873422047717645729[3] = 0;
   out_7873422047717645729[4] = 0;
   out_7873422047717645729[5] = 0;
   out_7873422047717645729[6] = 1;
   out_7873422047717645729[7] = 0;
   out_7873422047717645729[8] = 0;
   out_7873422047717645729[9] = 1;
   out_7873422047717645729[10] = 0;
   out_7873422047717645729[11] = 0;
   out_7873422047717645729[12] = 0;
   out_7873422047717645729[13] = 0;
   out_7873422047717645729[14] = 0;
   out_7873422047717645729[15] = 0;
   out_7873422047717645729[16] = 0;
   out_7873422047717645729[17] = 0;
   out_7873422047717645729[18] = 0;
   out_7873422047717645729[19] = 0;
   out_7873422047717645729[20] = 0;
   out_7873422047717645729[21] = 0;
   out_7873422047717645729[22] = 0;
   out_7873422047717645729[23] = 0;
   out_7873422047717645729[24] = 0;
   out_7873422047717645729[25] = 1;
   out_7873422047717645729[26] = 0;
   out_7873422047717645729[27] = 0;
   out_7873422047717645729[28] = 1;
   out_7873422047717645729[29] = 0;
   out_7873422047717645729[30] = 0;
   out_7873422047717645729[31] = 0;
   out_7873422047717645729[32] = 0;
   out_7873422047717645729[33] = 0;
   out_7873422047717645729[34] = 0;
   out_7873422047717645729[35] = 0;
   out_7873422047717645729[36] = 0;
   out_7873422047717645729[37] = 0;
   out_7873422047717645729[38] = 0;
   out_7873422047717645729[39] = 0;
   out_7873422047717645729[40] = 0;
   out_7873422047717645729[41] = 0;
   out_7873422047717645729[42] = 0;
   out_7873422047717645729[43] = 0;
   out_7873422047717645729[44] = 1;
   out_7873422047717645729[45] = 0;
   out_7873422047717645729[46] = 0;
   out_7873422047717645729[47] = 1;
   out_7873422047717645729[48] = 0;
   out_7873422047717645729[49] = 0;
   out_7873422047717645729[50] = 0;
   out_7873422047717645729[51] = 0;
   out_7873422047717645729[52] = 0;
   out_7873422047717645729[53] = 0;
}
void h_10(double *state, double *unused, double *out_4525655768187115008) {
   out_4525655768187115008[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_4525655768187115008[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_4525655768187115008[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_456117981794075216) {
   out_456117981794075216[0] = 0;
   out_456117981794075216[1] = 9.8100000000000005*cos(state[1]);
   out_456117981794075216[2] = 0;
   out_456117981794075216[3] = 0;
   out_456117981794075216[4] = -state[8];
   out_456117981794075216[5] = state[7];
   out_456117981794075216[6] = 0;
   out_456117981794075216[7] = state[5];
   out_456117981794075216[8] = -state[4];
   out_456117981794075216[9] = 0;
   out_456117981794075216[10] = 0;
   out_456117981794075216[11] = 0;
   out_456117981794075216[12] = 1;
   out_456117981794075216[13] = 0;
   out_456117981794075216[14] = 0;
   out_456117981794075216[15] = 1;
   out_456117981794075216[16] = 0;
   out_456117981794075216[17] = 0;
   out_456117981794075216[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_456117981794075216[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_456117981794075216[20] = 0;
   out_456117981794075216[21] = state[8];
   out_456117981794075216[22] = 0;
   out_456117981794075216[23] = -state[6];
   out_456117981794075216[24] = -state[5];
   out_456117981794075216[25] = 0;
   out_456117981794075216[26] = state[3];
   out_456117981794075216[27] = 0;
   out_456117981794075216[28] = 0;
   out_456117981794075216[29] = 0;
   out_456117981794075216[30] = 0;
   out_456117981794075216[31] = 1;
   out_456117981794075216[32] = 0;
   out_456117981794075216[33] = 0;
   out_456117981794075216[34] = 1;
   out_456117981794075216[35] = 0;
   out_456117981794075216[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_456117981794075216[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_456117981794075216[38] = 0;
   out_456117981794075216[39] = -state[7];
   out_456117981794075216[40] = state[6];
   out_456117981794075216[41] = 0;
   out_456117981794075216[42] = state[4];
   out_456117981794075216[43] = -state[3];
   out_456117981794075216[44] = 0;
   out_456117981794075216[45] = 0;
   out_456117981794075216[46] = 0;
   out_456117981794075216[47] = 0;
   out_456117981794075216[48] = 0;
   out_456117981794075216[49] = 0;
   out_456117981794075216[50] = 1;
   out_456117981794075216[51] = 0;
   out_456117981794075216[52] = 0;
   out_456117981794075216[53] = 1;
}
void h_13(double *state, double *unused, double *out_37028039399378348) {
   out_37028039399378348[0] = state[3];
   out_37028039399378348[1] = state[4];
   out_37028039399378348[2] = state[5];
}
void H_13(double *state, double *unused, double *out_262790839400944800) {
   out_262790839400944800[0] = 0;
   out_262790839400944800[1] = 0;
   out_262790839400944800[2] = 0;
   out_262790839400944800[3] = 1;
   out_262790839400944800[4] = 0;
   out_262790839400944800[5] = 0;
   out_262790839400944800[6] = 0;
   out_262790839400944800[7] = 0;
   out_262790839400944800[8] = 0;
   out_262790839400944800[9] = 0;
   out_262790839400944800[10] = 0;
   out_262790839400944800[11] = 0;
   out_262790839400944800[12] = 0;
   out_262790839400944800[13] = 0;
   out_262790839400944800[14] = 0;
   out_262790839400944800[15] = 0;
   out_262790839400944800[16] = 0;
   out_262790839400944800[17] = 0;
   out_262790839400944800[18] = 0;
   out_262790839400944800[19] = 0;
   out_262790839400944800[20] = 0;
   out_262790839400944800[21] = 0;
   out_262790839400944800[22] = 1;
   out_262790839400944800[23] = 0;
   out_262790839400944800[24] = 0;
   out_262790839400944800[25] = 0;
   out_262790839400944800[26] = 0;
   out_262790839400944800[27] = 0;
   out_262790839400944800[28] = 0;
   out_262790839400944800[29] = 0;
   out_262790839400944800[30] = 0;
   out_262790839400944800[31] = 0;
   out_262790839400944800[32] = 0;
   out_262790839400944800[33] = 0;
   out_262790839400944800[34] = 0;
   out_262790839400944800[35] = 0;
   out_262790839400944800[36] = 0;
   out_262790839400944800[37] = 0;
   out_262790839400944800[38] = 0;
   out_262790839400944800[39] = 0;
   out_262790839400944800[40] = 0;
   out_262790839400944800[41] = 1;
   out_262790839400944800[42] = 0;
   out_262790839400944800[43] = 0;
   out_262790839400944800[44] = 0;
   out_262790839400944800[45] = 0;
   out_262790839400944800[46] = 0;
   out_262790839400944800[47] = 0;
   out_262790839400944800[48] = 0;
   out_262790839400944800[49] = 0;
   out_262790839400944800[50] = 0;
   out_262790839400944800[51] = 0;
   out_262790839400944800[52] = 0;
   out_262790839400944800[53] = 0;
}
void h_14(double *state, double *unused, double *out_8155163407200643054) {
   out_8155163407200643054[0] = state[6];
   out_8155163407200643054[1] = state[7];
   out_8155163407200643054[2] = state[8];
}
void H_14(double *state, double *unused, double *out_7490533593696533591) {
   out_7490533593696533591[0] = 0;
   out_7490533593696533591[1] = 0;
   out_7490533593696533591[2] = 0;
   out_7490533593696533591[3] = 0;
   out_7490533593696533591[4] = 0;
   out_7490533593696533591[5] = 0;
   out_7490533593696533591[6] = 1;
   out_7490533593696533591[7] = 0;
   out_7490533593696533591[8] = 0;
   out_7490533593696533591[9] = 0;
   out_7490533593696533591[10] = 0;
   out_7490533593696533591[11] = 0;
   out_7490533593696533591[12] = 0;
   out_7490533593696533591[13] = 0;
   out_7490533593696533591[14] = 0;
   out_7490533593696533591[15] = 0;
   out_7490533593696533591[16] = 0;
   out_7490533593696533591[17] = 0;
   out_7490533593696533591[18] = 0;
   out_7490533593696533591[19] = 0;
   out_7490533593696533591[20] = 0;
   out_7490533593696533591[21] = 0;
   out_7490533593696533591[22] = 0;
   out_7490533593696533591[23] = 0;
   out_7490533593696533591[24] = 0;
   out_7490533593696533591[25] = 1;
   out_7490533593696533591[26] = 0;
   out_7490533593696533591[27] = 0;
   out_7490533593696533591[28] = 0;
   out_7490533593696533591[29] = 0;
   out_7490533593696533591[30] = 0;
   out_7490533593696533591[31] = 0;
   out_7490533593696533591[32] = 0;
   out_7490533593696533591[33] = 0;
   out_7490533593696533591[34] = 0;
   out_7490533593696533591[35] = 0;
   out_7490533593696533591[36] = 0;
   out_7490533593696533591[37] = 0;
   out_7490533593696533591[38] = 0;
   out_7490533593696533591[39] = 0;
   out_7490533593696533591[40] = 0;
   out_7490533593696533591[41] = 0;
   out_7490533593696533591[42] = 0;
   out_7490533593696533591[43] = 0;
   out_7490533593696533591[44] = 1;
   out_7490533593696533591[45] = 0;
   out_7490533593696533591[46] = 0;
   out_7490533593696533591[47] = 0;
   out_7490533593696533591[48] = 0;
   out_7490533593696533591[49] = 0;
   out_7490533593696533591[50] = 0;
   out_7490533593696533591[51] = 0;
   out_7490533593696533591[52] = 0;
   out_7490533593696533591[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_6404612215142923466) {
  err_fun(nom_x, delta_x, out_6404612215142923466);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8928511729536831732) {
  inv_err_fun(nom_x, true_x, out_8928511729536831732);
}
void pose_H_mod_fun(double *state, double *out_6801514816147998315) {
  H_mod_fun(state, out_6801514816147998315);
}
void pose_f_fun(double *state, double dt, double *out_9011020625270980343) {
  f_fun(state,  dt, out_9011020625270980343);
}
void pose_F_fun(double *state, double dt, double *out_5745440695796585215) {
  F_fun(state,  dt, out_5745440695796585215);
}
void pose_h_4(double *state, double *unused, double *out_3972431218962943054) {
  h_4(state, unused, out_3972431218962943054);
}
void pose_H_4(double *state, double *unused, double *out_7873422047717645729) {
  H_4(state, unused, out_7873422047717645729);
}
void pose_h_10(double *state, double *unused, double *out_4525655768187115008) {
  h_10(state, unused, out_4525655768187115008);
}
void pose_H_10(double *state, double *unused, double *out_456117981794075216) {
  H_10(state, unused, out_456117981794075216);
}
void pose_h_13(double *state, double *unused, double *out_37028039399378348) {
  h_13(state, unused, out_37028039399378348);
}
void pose_H_13(double *state, double *unused, double *out_262790839400944800) {
  H_13(state, unused, out_262790839400944800);
}
void pose_h_14(double *state, double *unused, double *out_8155163407200643054) {
  h_14(state, unused, out_8155163407200643054);
}
void pose_H_14(double *state, double *unused, double *out_7490533593696533591) {
  H_14(state, unused, out_7490533593696533591);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
