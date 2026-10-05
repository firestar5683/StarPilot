#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_6226893299276424900) {
   out_6226893299276424900[0] = delta_x[0] + nom_x[0];
   out_6226893299276424900[1] = delta_x[1] + nom_x[1];
   out_6226893299276424900[2] = delta_x[2] + nom_x[2];
   out_6226893299276424900[3] = delta_x[3] + nom_x[3];
   out_6226893299276424900[4] = delta_x[4] + nom_x[4];
   out_6226893299276424900[5] = delta_x[5] + nom_x[5];
   out_6226893299276424900[6] = delta_x[6] + nom_x[6];
   out_6226893299276424900[7] = delta_x[7] + nom_x[7];
   out_6226893299276424900[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3929429382952821600) {
   out_3929429382952821600[0] = -nom_x[0] + true_x[0];
   out_3929429382952821600[1] = -nom_x[1] + true_x[1];
   out_3929429382952821600[2] = -nom_x[2] + true_x[2];
   out_3929429382952821600[3] = -nom_x[3] + true_x[3];
   out_3929429382952821600[4] = -nom_x[4] + true_x[4];
   out_3929429382952821600[5] = -nom_x[5] + true_x[5];
   out_3929429382952821600[6] = -nom_x[6] + true_x[6];
   out_3929429382952821600[7] = -nom_x[7] + true_x[7];
   out_3929429382952821600[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_1271629825232555869) {
   out_1271629825232555869[0] = 1.0;
   out_1271629825232555869[1] = 0.0;
   out_1271629825232555869[2] = 0.0;
   out_1271629825232555869[3] = 0.0;
   out_1271629825232555869[4] = 0.0;
   out_1271629825232555869[5] = 0.0;
   out_1271629825232555869[6] = 0.0;
   out_1271629825232555869[7] = 0.0;
   out_1271629825232555869[8] = 0.0;
   out_1271629825232555869[9] = 0.0;
   out_1271629825232555869[10] = 1.0;
   out_1271629825232555869[11] = 0.0;
   out_1271629825232555869[12] = 0.0;
   out_1271629825232555869[13] = 0.0;
   out_1271629825232555869[14] = 0.0;
   out_1271629825232555869[15] = 0.0;
   out_1271629825232555869[16] = 0.0;
   out_1271629825232555869[17] = 0.0;
   out_1271629825232555869[18] = 0.0;
   out_1271629825232555869[19] = 0.0;
   out_1271629825232555869[20] = 1.0;
   out_1271629825232555869[21] = 0.0;
   out_1271629825232555869[22] = 0.0;
   out_1271629825232555869[23] = 0.0;
   out_1271629825232555869[24] = 0.0;
   out_1271629825232555869[25] = 0.0;
   out_1271629825232555869[26] = 0.0;
   out_1271629825232555869[27] = 0.0;
   out_1271629825232555869[28] = 0.0;
   out_1271629825232555869[29] = 0.0;
   out_1271629825232555869[30] = 1.0;
   out_1271629825232555869[31] = 0.0;
   out_1271629825232555869[32] = 0.0;
   out_1271629825232555869[33] = 0.0;
   out_1271629825232555869[34] = 0.0;
   out_1271629825232555869[35] = 0.0;
   out_1271629825232555869[36] = 0.0;
   out_1271629825232555869[37] = 0.0;
   out_1271629825232555869[38] = 0.0;
   out_1271629825232555869[39] = 0.0;
   out_1271629825232555869[40] = 1.0;
   out_1271629825232555869[41] = 0.0;
   out_1271629825232555869[42] = 0.0;
   out_1271629825232555869[43] = 0.0;
   out_1271629825232555869[44] = 0.0;
   out_1271629825232555869[45] = 0.0;
   out_1271629825232555869[46] = 0.0;
   out_1271629825232555869[47] = 0.0;
   out_1271629825232555869[48] = 0.0;
   out_1271629825232555869[49] = 0.0;
   out_1271629825232555869[50] = 1.0;
   out_1271629825232555869[51] = 0.0;
   out_1271629825232555869[52] = 0.0;
   out_1271629825232555869[53] = 0.0;
   out_1271629825232555869[54] = 0.0;
   out_1271629825232555869[55] = 0.0;
   out_1271629825232555869[56] = 0.0;
   out_1271629825232555869[57] = 0.0;
   out_1271629825232555869[58] = 0.0;
   out_1271629825232555869[59] = 0.0;
   out_1271629825232555869[60] = 1.0;
   out_1271629825232555869[61] = 0.0;
   out_1271629825232555869[62] = 0.0;
   out_1271629825232555869[63] = 0.0;
   out_1271629825232555869[64] = 0.0;
   out_1271629825232555869[65] = 0.0;
   out_1271629825232555869[66] = 0.0;
   out_1271629825232555869[67] = 0.0;
   out_1271629825232555869[68] = 0.0;
   out_1271629825232555869[69] = 0.0;
   out_1271629825232555869[70] = 1.0;
   out_1271629825232555869[71] = 0.0;
   out_1271629825232555869[72] = 0.0;
   out_1271629825232555869[73] = 0.0;
   out_1271629825232555869[74] = 0.0;
   out_1271629825232555869[75] = 0.0;
   out_1271629825232555869[76] = 0.0;
   out_1271629825232555869[77] = 0.0;
   out_1271629825232555869[78] = 0.0;
   out_1271629825232555869[79] = 0.0;
   out_1271629825232555869[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_6661690039012274114) {
   out_6661690039012274114[0] = state[0];
   out_6661690039012274114[1] = state[1];
   out_6661690039012274114[2] = state[2];
   out_6661690039012274114[3] = state[3];
   out_6661690039012274114[4] = state[4];
   out_6661690039012274114[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_6661690039012274114[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_6661690039012274114[7] = state[7];
   out_6661690039012274114[8] = state[8];
}
void F_fun(double *state, double dt, double *out_1834203406066241770) {
   out_1834203406066241770[0] = 1;
   out_1834203406066241770[1] = 0;
   out_1834203406066241770[2] = 0;
   out_1834203406066241770[3] = 0;
   out_1834203406066241770[4] = 0;
   out_1834203406066241770[5] = 0;
   out_1834203406066241770[6] = 0;
   out_1834203406066241770[7] = 0;
   out_1834203406066241770[8] = 0;
   out_1834203406066241770[9] = 0;
   out_1834203406066241770[10] = 1;
   out_1834203406066241770[11] = 0;
   out_1834203406066241770[12] = 0;
   out_1834203406066241770[13] = 0;
   out_1834203406066241770[14] = 0;
   out_1834203406066241770[15] = 0;
   out_1834203406066241770[16] = 0;
   out_1834203406066241770[17] = 0;
   out_1834203406066241770[18] = 0;
   out_1834203406066241770[19] = 0;
   out_1834203406066241770[20] = 1;
   out_1834203406066241770[21] = 0;
   out_1834203406066241770[22] = 0;
   out_1834203406066241770[23] = 0;
   out_1834203406066241770[24] = 0;
   out_1834203406066241770[25] = 0;
   out_1834203406066241770[26] = 0;
   out_1834203406066241770[27] = 0;
   out_1834203406066241770[28] = 0;
   out_1834203406066241770[29] = 0;
   out_1834203406066241770[30] = 1;
   out_1834203406066241770[31] = 0;
   out_1834203406066241770[32] = 0;
   out_1834203406066241770[33] = 0;
   out_1834203406066241770[34] = 0;
   out_1834203406066241770[35] = 0;
   out_1834203406066241770[36] = 0;
   out_1834203406066241770[37] = 0;
   out_1834203406066241770[38] = 0;
   out_1834203406066241770[39] = 0;
   out_1834203406066241770[40] = 1;
   out_1834203406066241770[41] = 0;
   out_1834203406066241770[42] = 0;
   out_1834203406066241770[43] = 0;
   out_1834203406066241770[44] = 0;
   out_1834203406066241770[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_1834203406066241770[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_1834203406066241770[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1834203406066241770[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_1834203406066241770[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_1834203406066241770[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_1834203406066241770[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_1834203406066241770[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_1834203406066241770[53] = -9.8100000000000005*dt;
   out_1834203406066241770[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_1834203406066241770[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_1834203406066241770[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1834203406066241770[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1834203406066241770[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_1834203406066241770[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_1834203406066241770[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_1834203406066241770[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_1834203406066241770[62] = 0;
   out_1834203406066241770[63] = 0;
   out_1834203406066241770[64] = 0;
   out_1834203406066241770[65] = 0;
   out_1834203406066241770[66] = 0;
   out_1834203406066241770[67] = 0;
   out_1834203406066241770[68] = 0;
   out_1834203406066241770[69] = 0;
   out_1834203406066241770[70] = 1;
   out_1834203406066241770[71] = 0;
   out_1834203406066241770[72] = 0;
   out_1834203406066241770[73] = 0;
   out_1834203406066241770[74] = 0;
   out_1834203406066241770[75] = 0;
   out_1834203406066241770[76] = 0;
   out_1834203406066241770[77] = 0;
   out_1834203406066241770[78] = 0;
   out_1834203406066241770[79] = 0;
   out_1834203406066241770[80] = 1;
}
void h_25(double *state, double *unused, double *out_1060401645907473267) {
   out_1060401645907473267[0] = state[6];
}
void H_25(double *state, double *unused, double *out_7492528034826712728) {
   out_7492528034826712728[0] = 0;
   out_7492528034826712728[1] = 0;
   out_7492528034826712728[2] = 0;
   out_7492528034826712728[3] = 0;
   out_7492528034826712728[4] = 0;
   out_7492528034826712728[5] = 0;
   out_7492528034826712728[6] = 1;
   out_7492528034826712728[7] = 0;
   out_7492528034826712728[8] = 0;
}
void h_24(double *state, double *unused, double *out_8639369439479545960) {
   out_8639369439479545960[0] = state[4];
   out_8639369439479545960[1] = state[5];
}
void H_24(double *state, double *unused, double *out_8239110267165924544) {
   out_8239110267165924544[0] = 0;
   out_8239110267165924544[1] = 0;
   out_8239110267165924544[2] = 0;
   out_8239110267165924544[3] = 0;
   out_8239110267165924544[4] = 1;
   out_8239110267165924544[5] = 0;
   out_8239110267165924544[6] = 0;
   out_8239110267165924544[7] = 0;
   out_8239110267165924544[8] = 0;
   out_8239110267165924544[9] = 0;
   out_8239110267165924544[10] = 0;
   out_8239110267165924544[11] = 0;
   out_8239110267165924544[12] = 0;
   out_8239110267165924544[13] = 0;
   out_8239110267165924544[14] = 1;
   out_8239110267165924544[15] = 0;
   out_8239110267165924544[16] = 0;
   out_8239110267165924544[17] = 0;
}
void h_30(double *state, double *unused, double *out_7831236872257824203) {
   out_7831236872257824203[0] = state[4];
}
void H_30(double *state, double *unused, double *out_4037525697391222133) {
   out_4037525697391222133[0] = 0;
   out_4037525697391222133[1] = 0;
   out_4037525697391222133[2] = 0;
   out_4037525697391222133[3] = 0;
   out_4037525697391222133[4] = 1;
   out_4037525697391222133[5] = 0;
   out_4037525697391222133[6] = 0;
   out_4037525697391222133[7] = 0;
   out_4037525697391222133[8] = 0;
}
void h_26(double *state, double *unused, double *out_8434552756934301720) {
   out_8434552756934301720[0] = state[7];
}
void H_26(double *state, double *unused, double *out_7649690069122038287) {
   out_7649690069122038287[0] = 0;
   out_7649690069122038287[1] = 0;
   out_7649690069122038287[2] = 0;
   out_7649690069122038287[3] = 0;
   out_7649690069122038287[4] = 0;
   out_7649690069122038287[5] = 0;
   out_7649690069122038287[6] = 0;
   out_7649690069122038287[7] = 1;
   out_7649690069122038287[8] = 0;
}
void h_27(double *state, double *unused, double *out_3941271621753372378) {
   out_3941271621753372378[0] = state[3];
}
void H_27(double *state, double *unused, double *out_6212289009191647044) {
   out_6212289009191647044[0] = 0;
   out_6212289009191647044[1] = 0;
   out_6212289009191647044[2] = 0;
   out_6212289009191647044[3] = 1;
   out_6212289009191647044[4] = 0;
   out_6212289009191647044[5] = 0;
   out_6212289009191647044[6] = 0;
   out_6212289009191647044[7] = 0;
   out_6212289009191647044[8] = 0;
}
void h_29(double *state, double *unused, double *out_7578721150007394728) {
   out_7578721150007394728[0] = state[1];
}
void H_29(double *state, double *unused, double *out_7925651736061198077) {
   out_7925651736061198077[0] = 0;
   out_7925651736061198077[1] = 1;
   out_7925651736061198077[2] = 0;
   out_7925651736061198077[3] = 0;
   out_7925651736061198077[4] = 0;
   out_7925651736061198077[5] = 0;
   out_7925651736061198077[6] = 0;
   out_7925651736061198077[7] = 0;
   out_7925651736061198077[8] = 0;
}
void h_28(double *state, double *unused, double *out_2997761768851709943) {
   out_2997761768851709943[0] = state[0];
}
void H_28(double *state, double *unused, double *out_5438693320578822965) {
   out_5438693320578822965[0] = 1;
   out_5438693320578822965[1] = 0;
   out_5438693320578822965[2] = 0;
   out_5438693320578822965[3] = 0;
   out_5438693320578822965[4] = 0;
   out_5438693320578822965[5] = 0;
   out_5438693320578822965[6] = 0;
   out_5438693320578822965[7] = 0;
   out_5438693320578822965[8] = 0;
}
void h_31(double *state, double *unused, double *out_390229746721409900) {
   out_390229746721409900[0] = state[8];
}
void H_31(double *state, double *unused, double *out_7523173996703673156) {
   out_7523173996703673156[0] = 0;
   out_7523173996703673156[1] = 0;
   out_7523173996703673156[2] = 0;
   out_7523173996703673156[3] = 0;
   out_7523173996703673156[4] = 0;
   out_7523173996703673156[5] = 0;
   out_7523173996703673156[6] = 0;
   out_7523173996703673156[7] = 0;
   out_7523173996703673156[8] = 1;
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

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_6226893299276424900) {
  err_fun(nom_x, delta_x, out_6226893299276424900);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3929429382952821600) {
  inv_err_fun(nom_x, true_x, out_3929429382952821600);
}
void car_H_mod_fun(double *state, double *out_1271629825232555869) {
  H_mod_fun(state, out_1271629825232555869);
}
void car_f_fun(double *state, double dt, double *out_6661690039012274114) {
  f_fun(state,  dt, out_6661690039012274114);
}
void car_F_fun(double *state, double dt, double *out_1834203406066241770) {
  F_fun(state,  dt, out_1834203406066241770);
}
void car_h_25(double *state, double *unused, double *out_1060401645907473267) {
  h_25(state, unused, out_1060401645907473267);
}
void car_H_25(double *state, double *unused, double *out_7492528034826712728) {
  H_25(state, unused, out_7492528034826712728);
}
void car_h_24(double *state, double *unused, double *out_8639369439479545960) {
  h_24(state, unused, out_8639369439479545960);
}
void car_H_24(double *state, double *unused, double *out_8239110267165924544) {
  H_24(state, unused, out_8239110267165924544);
}
void car_h_30(double *state, double *unused, double *out_7831236872257824203) {
  h_30(state, unused, out_7831236872257824203);
}
void car_H_30(double *state, double *unused, double *out_4037525697391222133) {
  H_30(state, unused, out_4037525697391222133);
}
void car_h_26(double *state, double *unused, double *out_8434552756934301720) {
  h_26(state, unused, out_8434552756934301720);
}
void car_H_26(double *state, double *unused, double *out_7649690069122038287) {
  H_26(state, unused, out_7649690069122038287);
}
void car_h_27(double *state, double *unused, double *out_3941271621753372378) {
  h_27(state, unused, out_3941271621753372378);
}
void car_H_27(double *state, double *unused, double *out_6212289009191647044) {
  H_27(state, unused, out_6212289009191647044);
}
void car_h_29(double *state, double *unused, double *out_7578721150007394728) {
  h_29(state, unused, out_7578721150007394728);
}
void car_H_29(double *state, double *unused, double *out_7925651736061198077) {
  H_29(state, unused, out_7925651736061198077);
}
void car_h_28(double *state, double *unused, double *out_2997761768851709943) {
  h_28(state, unused, out_2997761768851709943);
}
void car_H_28(double *state, double *unused, double *out_5438693320578822965) {
  H_28(state, unused, out_5438693320578822965);
}
void car_h_31(double *state, double *unused, double *out_390229746721409900) {
  h_31(state, unused, out_390229746721409900);
}
void car_H_31(double *state, double *unused, double *out_7523173996703673156) {
  H_31(state, unused, out_7523173996703673156);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
